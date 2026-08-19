# Analisador Viral

Aplicativo desktop em Python que analisa canais do YouTube e mostra quais dos últimos vídeos mais viralizaram — com gráficos e uma análise dos possíveis motivos.

## Como funciona

1. Você abre o aplicativo
2. Cola o link de um canal do YouTube
3. O programa busca os últimos 10 vídeos via YouTube Data API v3
4. Exibe gráficos de views, likes e comentários
5. Identifica o(s) vídeo(s) que fugiu(ram) da média do canal e sugere hipóteses do porquê

## Tecnologias

- **Python 3.13**
- **CustomTkinter** — interface gráfica moderna
- **YouTube Data API v3** — coleta oficial de dados
- **pandas** — manipulação dos dados
- **matplotlib** — geração dos gráficos
- **PyInstaller** — empacotamento em `.exe`

## Instalação (modo desenvolvedor)

```bash
git clone https://github.com/SEU_USUARIO/analisador-viral.git
cd analisador-viral
pip install -r requirements.txt
python app.py
```

Na primeira execução o programa pede sua chave da YouTube Data API v3 e salva localmente. Para gerar uma chave gratuita, siga: https://console.cloud.google.com/ → criar projeto → ativar "YouTube Data API v3" → criar credencial do tipo "Chave de API".

## Uso via executável

Baixe o `.exe` mais recente na aba **Releases** deste repositório, clique duas vezes e pronto. Não é necessário ter Python instalado.

## Estrutura do projeto

```
analisador-viral/
├── src/
│   ├── youtube_client.py    # Comunicação com a API do YouTube
│   ├── analyzer.py          # Lógica de detecção de virais
│   └── visualizer.py        # Geração dos gráficos
├── app.py                   # Interface gráfica (CustomTkinter)
├── build.py                 # Script para gerar o executável
├── requirements.txt
└── README.md
```

## Status

Em desenvolvimento.

## Licença

MIT
