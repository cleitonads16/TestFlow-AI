import pytest
from docx import Document
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ia import CasoTesteGerado, LLMProvider
from modelos import (
    Base,
    CategoriaCasoDeTeste,
    Escopo,
    GeracaoIA,
    OrigemCasoDeTeste,
    Prioridade,
    Projeto,
    StatusEscopo,
)
from servicos import processar_escopo


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


@pytest.fixture
def sessao(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'teste.db'}")
    Base.metadata.create_all(engine)
    Sessao = sessionmaker(bind=engine)
    with Sessao() as sessao:
        yield sessao


@pytest.fixture
def arquivo_escopo(tmp_path):
    caminho = tmp_path / "escopo.docx"
    documento = Document()
    documento.add_paragraph("O sistema deve permitir login de usuários cadastrados.")
    documento.save(caminho)
    return caminho


def _criar_escopo(sessao, nome_arquivo="escopo.docx"):
    projeto = Projeto(nome="PDI - Gestor de Casos de Teste", descricao="Projeto de teste")
    escopo = Escopo(nome_arquivo=nome_arquivo, projeto=projeto)
    sessao.add(projeto)
    sessao.add(escopo)
    sessao.commit()
    return escopo


def test_processar_escopo_persiste_casos_e_registra_auditoria(sessao, arquivo_escopo):
    escopo = _criar_escopo(sessao)
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

    casos = processar_escopo(sessao, escopo, arquivo_escopo, provedor)

    assert len(casos) == 1
    assert casos[0].codigo == "CT-001"
    assert casos[0].origem == OrigemCasoDeTeste.IA
    assert casos[0].escopo_id == escopo.id
    assert escopo.status == StatusEscopo.PROCESSADO
    assert "login" in escopo.texto_extraido.lower()

    geracao = sessao.query(GeracaoIA).one()
    assert geracao.provedor == "falso"
    assert geracao.modelo == "modelo-de-teste"
    assert geracao.quantidade_casos_gerados == 1
    assert geracao.tokens_utilizados == 123
    assert geracao.escopo_id == escopo.id


def test_processar_escopo_marca_erro_quando_ia_falha(sessao, arquivo_escopo):
    escopo = _criar_escopo(sessao)
    provedor = _ProvedorFalso(erro=RuntimeError("falha simulada na IA"))

    with pytest.raises(RuntimeError):
        processar_escopo(sessao, escopo, arquivo_escopo, provedor)

    assert escopo.status == StatusEscopo.ERRO
    assert sessao.query(GeracaoIA).count() == 0


def test_processar_escopo_marca_erro_quando_extracao_falha(sessao, tmp_path):
    escopo = _criar_escopo(sessao, nome_arquivo="escopo.txt")
    caminho_nao_suportado = tmp_path / "escopo.txt"
    caminho_nao_suportado.write_text("conteúdo qualquer", encoding="utf-8")
    provedor = _ProvedorFalso()

    with pytest.raises(ValueError):
        processar_escopo(sessao, escopo, caminho_nao_suportado, provedor)

    assert escopo.status == StatusEscopo.ERRO
    assert sessao.query(GeracaoIA).count() == 0
