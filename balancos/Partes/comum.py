import re

def nome_ficheiro_regiao(regiao: str) -> str:
    """Nome de ficheiro do relatório a partir da região.
    Fonte única da verdade: quem escreve E quem lê chamam ISTO."""
    nome = re.sub(r'[^a-zA-Z0-9\s\-]', '', str(regiao).strip())
    nome = re.sub(r'\s+', '_', nome)
    nome = re.sub(r'_+', '_', nome)
    nome = nome.strip('_')
    return nome[:70]