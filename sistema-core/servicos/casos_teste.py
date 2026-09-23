from modelos import CategoriaCasoDeTeste, OrigemCasoDeTeste, Prioridade
from modelos.models import CasoDeTeste, Escopo

from .erros import OperacaoEmConflito, RegraDeNegocioViolada, converter_enum, exigir_texto

_CAMPOS_EDITAVEIS = {
    "codigo",
    "titulo",
    "categoria",
    "pre_condicao",
    "passos",
    "resultado_esperado",
    "prioridade",
}


def criar_caso_teste(
    escopo: Escopo,
    codigo: str,
    titulo: str,
    categoria: CategoriaCasoDeTeste | str = CategoriaCasoDeTeste.FUNCIONAL,
    pre_condicao: str | None = None,
    passos: str | None = None,
    resultado_esperado: str | None = None,
    prioridade: Prioridade | str = Prioridade.MEDIA,
) -> CasoDeTeste:
    """Cria um caso de teste manual (origem="manual") vinculado ao escopo.

    O código do caso é único dentro do escopo, para que a equipe possa
    referenciá-lo sem ambiguidade nas rodadas de execução.
    """
    codigo = exigir_texto(codigo, "codigo")
    _garantir_codigo_disponivel(escopo, codigo)

    return CasoDeTeste.objects.create(
        escopo=escopo,
        codigo=codigo,
        titulo=exigir_texto(titulo, "titulo"),
        categoria=converter_enum(CategoriaCasoDeTeste, categoria, "categoria").value,
        pre_condicao=pre_condicao,
        passos=passos,
        resultado_esperado=resultado_esperado,
        prioridade=converter_enum(Prioridade, prioridade, "prioridade").value,
        origem=OrigemCasoDeTeste.MANUAL.value,
    )


def listar_casos_teste(
    escopo: Escopo | None = None,
    projeto_id: int | None = None,
    categoria: CategoriaCasoDeTeste | str | None = None,
    origem: OrigemCasoDeTeste | str | None = None,
) -> list[CasoDeTeste]:
    consulta = CasoDeTeste.objects.select_related("escopo").order_by("escopo_id", "codigo")
    if escopo is not None:
        consulta = consulta.filter(escopo=escopo)
    if projeto_id is not None:
        consulta = consulta.filter(escopo__projeto_id=projeto_id)
    if categoria is not None:
        consulta = consulta.filter(
            categoria=converter_enum(CategoriaCasoDeTeste, categoria, "categoria").value
        )
    if origem is not None:
        consulta = consulta.filter(
            origem=converter_enum(OrigemCasoDeTeste, origem, "origem").value
        )
    return list(consulta)


def atualizar_caso_teste(caso: CasoDeTeste, **campos) -> CasoDeTeste:
    """Atualiza os campos informados; vale também para casos gerados por IA (revisão do usuário).

    A origem não muda: um caso gerado por IA e revisado continua registrado
    como "ia", preservando a rastreabilidade da geração.
    """
    nao_editaveis = set(campos) - _CAMPOS_EDITAVEIS
    if nao_editaveis:
        raise RegraDeNegocioViolada(
            f"Campos não editáveis: {', '.join(sorted(nao_editaveis))}."
        )

    if "codigo" in campos:
        novo_codigo = exigir_texto(campos["codigo"], "codigo")
        if novo_codigo != caso.codigo:
            _garantir_codigo_disponivel(caso.escopo, novo_codigo)
        campos["codigo"] = novo_codigo
    if "titulo" in campos:
        campos["titulo"] = exigir_texto(campos["titulo"], "titulo")
    if "categoria" in campos:
        campos["categoria"] = converter_enum(
            CategoriaCasoDeTeste, campos["categoria"], "categoria"
        ).value
    if "prioridade" in campos:
        campos["prioridade"] = converter_enum(
            Prioridade, campos["prioridade"], "prioridade"
        ).value

    for nome, valor in campos.items():
        setattr(caso, nome, valor)
    caso.save()
    return caso


def obter_casos_por_ids(ids: list[int]) -> list[CasoDeTeste]:
    """Busca os casos na ordem informada; recusa a lista inteira se algum id não existir."""
    encontrados = CasoDeTeste.objects.select_related("escopo").in_bulk(ids)
    faltando = [str(caso_id) for caso_id in dict.fromkeys(ids) if caso_id not in encontrados]
    if faltando:
        raise RegraDeNegocioViolada(f"Casos de teste não encontrados: {', '.join(faltando)}.")
    return [encontrados[caso_id] for caso_id in ids]


def excluir_caso_teste(caso: CasoDeTeste) -> None:
    """Exclui o caso, desde que ele nunca tenha entrado em uma rodada de execução.

    Excluir um caso já executado apagaria em cascata o histórico de execuções
    e defeitos, então isso é recusado.
    """
    if caso.execucoes.exists():
        raise OperacaoEmConflito(
            f"O caso {caso.codigo} já faz parte de rodadas de execução e não pode ser excluído."
        )
    caso.delete()


def _garantir_codigo_disponivel(escopo: Escopo, codigo: str) -> None:
    if CasoDeTeste.objects.filter(escopo=escopo, codigo=codigo).exists():
        raise OperacaoEmConflito(
            f"Já existe um caso de teste com o código {codigo} neste escopo."
        )
