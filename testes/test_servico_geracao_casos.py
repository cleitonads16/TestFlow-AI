import pytest
from docx import Document

from ia import CasoTesteGerado, LLMProvider
from modelos import CategoriaCasoDeTeste, OrigemCasoDeTeste, Prioridade, StatusEscopo
from modelos.models import CasoDeTeste, Escopo, GeracaoIA, Projeto
from servicos import RegraDeNegocioViolada, processar_escopo


class _ProvedorFalso(LLMProvider):
    """Dublê de LLMProvider — evita chamar a API real de IA nos testes do serviço."""

    def __init__(self, casos=None, erro=None, tokens=None):
        self._casos = casos or []
        self._erro = erro
        self._tokens = tokens

    @property
    def nome(self) -> str:
        return "falso"

    @property
    def modelo(self) -> str:
        return "modelo-de-teste"

    @property
    def ultimo_tokens_utilizados(self):
        return self._tokens

    def gerar_casos_teste(self, texto_escopo: str) -> list[CasoTesteGerado]:
        if self._erro is not None:
            raise self._erro
        return self._casos


pytestmark = pytest.mark.django_db


@pytest.fixture
def arquivo_escopo(tmp_path):
    caminho = tmp_path / "escopo.docx"
    documento = Document()
    documento.add_paragraph("O sistema deve permitir login de usuários cadastrados.")
    documento.save(caminho)
    return caminho


def _criar_escopo(nome_arquivo="escopo.docx"):
    projeto = Projeto.objects.create(
        nome="PDI - Gestor de Casos de Teste", descricao="Projeto de teste"
    )
    return Escopo.objects.create(nome_arquivo=nome_arquivo, projeto=projeto)


def test_processar_escopo_persiste_casos_e_registra_auditoria(arquivo_escopo):
    escopo = _criar_escopo()
    caso_gerado = CasoTesteGerado(
        codigo="CT-001",
        titulo="Validar login",
        categoria=CategoriaCasoDeTeste.FUNCIONAL,
        pre_condicao="Usuário cadastrado",
        passos="1. Acessar tela de login\n2. Informar credenciais",
        resultado_esperado="Usuário autenticado com sucesso",
        prioridade=Prioridade.ALTA,
    )
    provedor = _ProvedorFalso(casos=[caso_gerado], tokens=123)

    casos = processar_escopo(escopo, arquivo_escopo, provedor)

    assert len(casos) == 1
    assert casos[0].codigo == "CT-001"
    assert casos[0].origem == OrigemCasoDeTeste.IA
    assert casos[0].escopo_id == escopo.id
    escopo.refresh_from_db()
    assert escopo.status == StatusEscopo.PROCESSADO
    assert "login" in escopo.texto_extraido.lower()
    assert CasoDeTeste.objects.filter(escopo=escopo).count() == 1

    geracao = GeracaoIA.objects.get()
    assert geracao.provedor == "falso"
    assert geracao.modelo == "modelo-de-teste"
    assert geracao.quantidade_casos_gerados == 1
    assert geracao.tokens_utilizados == 123
    assert geracao.escopo_id == escopo.id


def test_processar_escopo_marca_erro_quando_ia_falha(arquivo_escopo):
    escopo = _criar_escopo()
    provedor = _ProvedorFalso(erro=RuntimeError("falha simulada na IA"))

    with pytest.raises(RuntimeError):
        processar_escopo(escopo, arquivo_escopo, provedor)

    escopo.refresh_from_db()
    assert escopo.status == StatusEscopo.ERRO
    assert GeracaoIA.objects.count() == 0
    assert CasoDeTeste.objects.count() == 0


def test_processar_escopo_marca_erro_quando_extracao_falha(tmp_path):
    escopo = _criar_escopo(nome_arquivo="escopo.txt")
    caminho_nao_suportado = tmp_path / "escopo.txt"
    caminho_nao_suportado.write_text("conteúdo qualquer", encoding="utf-8")
    provedor = _ProvedorFalso()

    with pytest.raises(ValueError):
        processar_escopo(escopo, caminho_nao_suportado, provedor)

    escopo.refresh_from_db()
    assert escopo.status == StatusEscopo.ERRO
    assert GeracaoIA.objects.count() == 0
    assert CasoDeTeste.objects.count() == 0


def test_processar_escopo_recusa_escopo_ja_processado(arquivo_escopo):
    escopo = _criar_escopo()
    escopo.status = StatusEscopo.PROCESSADO.value
    escopo.save()

    with pytest.raises(RegraDeNegocioViolada, match="já foi processado"):
        processar_escopo(escopo, arquivo_escopo, _ProvedorFalso())

    assert GeracaoIA.objects.count() == 0


def test_processar_escopo_permite_nova_tentativa_apos_erro(arquivo_escopo):
    escopo = _criar_escopo()
    escopo.status = StatusEscopo.ERRO.value
    escopo.save()

    processar_escopo(escopo, arquivo_escopo, _ProvedorFalso())

    escopo.refresh_from_db()
    assert escopo.status == StatusEscopo.PROCESSADO
