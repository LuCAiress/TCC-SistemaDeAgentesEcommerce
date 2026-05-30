from pathlib import Path

from graph import build_graph


def salvar_grafo_png(output_path: str = "images/grafo.png") -> str:
    """Gera a imagem PNG do grafo e salva no caminho informado."""
    compiled_graph = build_graph()
    png_bytes = compiled_graph.get_graph().draw_mermaid_png()

    caminho_saida = Path(output_path)
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    caminho_saida.write_bytes(png_bytes)

    return str(caminho_saida)


if __name__ == "__main__":
    caminho = salvar_grafo_png()
    print(f"Imagem salva em: {caminho}")