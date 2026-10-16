# BioFace

Protótipo web local de identificação facial 1:N. O sistema captura uma imagem pela webcam ou aceita uma foto enviada, compara o rosto com os perfis cadastrados e apresenta o resultado e as etapas do processamento.

> **Escopo:** projeto acadêmico demonstrativo. Não oferece proteção suficiente para controlar acesso real: não possui prova de vida, proteção contra fotos reproduzidas, armazenamento biométrico criptografado nem autorização aplicada a rotas protegidas.

## Requisitos

- Windows 10 ou 11;
- Python instalado e disponível pelo comando `py`;
- conexão com a internet durante a instalação das dependências;
- webcam, ou uma imagem JPEG/PNG;
- para usar a webcam por outro dispositivo da rede: `mkcert`, certificado confiável nesse dispositivo e ambos na mesma rede local.
- para executar com Docker: Docker Desktop com Docker Compose disponível.

## Executar com Docker

Com o Docker Desktop instalado e aberto, abra um terminal na pasta do projeto e execute:

```powershell
docker compose up --build
```

Na primeira execução, o Docker baixa a imagem base e instala as dependências (incluindo a compilação do dlib), portanto a preparação pode demorar. Depois, abra <http://localhost:5000>. A webcam pode ser usada no próprio computador pelo endereço `localhost`; acessar pelo IP da rede em HTTP não habilita a webcam em navegadores modernos.

Os dados são mantidos nas pastas locais `data/` e `instance/`, montadas no contêiner. O arquivo `data/users.json` é criado vazio na primeira execução; cadastros e capturas permanecem no computador mesmo que o contêiner seja recriado. Para encerrar, pressione `Ctrl+C`; para iniciar novamente em segundo plano, use `docker compose up -d`. Para parar esse modo, execute `docker compose down`.

O Docker usa `requirements-docker.txt` com `opencv-python-headless`, pois o processamento ocorre no servidor e não abre janelas gráficas; a instalação local do Windows continua usando `requirements.txt`. Para a webcam de outro dispositivo, será necessário configurar HTTPS confiável para esse endereço; os certificados locais do mkcert não são incluídos na imagem.

O `dlib` pode precisar ser compilado no Windows. Se a instalação do projeto falhar especificamente ao construir o `dlib`, instale o Visual Studio Build Tools com a carga de trabalho **Desenvolvimento para desktop com C++** e tente novamente. A dependência `setuptools<82` está fixada para compatibilidade com `face_recognition_models`.

## Instalação e execução

Abra o PowerShell na pasta do projeto e execute:

```powershell
py -m pip install -r requirements.txt
py run.py
```

Abra o endereço impresso pelo programa. Sem certificado, use `http://localhost:5000` no próprio computador. O acesso pelo IP da rede em HTTP não permite que navegadores modernos liberem a webcam ao vivo.

### Webcam por HTTPS na rede local (Windows)

O HTTPS é necessário para que o navegador permita o uso da webcam em outro dispositivo. No computador que executa o servidor:

1. Instale o `mkcert`:

   ```powershell
   winget install --id FiloSottile.mkcert --exact
   ```

2. Feche e abra o PowerShell. Entre na pasta do projeto. Se a política de execução bloquear o script, libere a execução apenas para a janela atual:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   ```

3. Gere e instale os certificados locais:

   ```powershell
   .\scripts\setup_https.ps1
   ```

   O script instala a autoridade certificadora local no computador servidor e gera um certificado para `localhost`, `127.0.0.1` e o IP atual da rede.

4. Inicie ou reinicie o servidor:

   ```powershell
   py run.py
   ```

5. Abra o endereço `https://...` impresso no terminal. Se o Firewall do Windows perguntar, permita o acesso em redes privadas.

No próprio computador, o certificado é confiável após o passo 3. Em outro PC Windows, copie somente `certs/rootCA.pem` para o dispositivo cliente e execute no PowerShell, na pasta onde o arquivo foi copiado:

```powershell
certutil -addstore -user Root .\rootCA.pem
```

Feche e reabra o navegador. O cliente e o servidor precisam estar na mesma rede. Em celular, o procedimento para confiar numa autoridade certificadora varia conforme o sistema operacional e o navegador; o QR code apenas abre a página e não instala o certificado.

Se o IP local mudar, execute o script de HTTPS novamente e reinicie o servidor. **Nunca compartilhe `rootCA-key.pem`**. Os certificados e chaves são locais e ignorados pelo Git.

## Como usar

1. Acesse **Cadastros**, informe o nome e escolha um nível de acesso (1, 2 ou 3).
2. Ative a webcam e capture uma foto, selecione uma ou mais fotos, ou combine os dois métodos. Cada imagem válida precisa conter exatamente um rosto.
3. Na tela principal, capture o rosto ou escolha uma imagem e selecione **Verificar identidade**.
4. Consulte o resultado e abra **Ver detalhes da verificação** para visualizar as imagens intermediárias, as etapas, o vetor biométrico e a comparação 1:N.

A página principal exibe um QR code para abrir o BioFace em outro dispositivo. Esse endereço abre a página principal; no celular, use **Cadastros** para cadastrar um perfil.

## Arquitetura e fluxo

- `run.py` cria a aplicação Flask, localiza o IP da rede e ativa HTTPS se os arquivos de certificado existirem em `certs/`.
- `app/__init__.py` configura limites de requisição, caminhos de dados e o limiar de comparação (`MATCH_TOLERANCE = 0.60`) e registra as rotas.
- `app/routes/main.py` atende as páginas, recebe as imagens, valida a captura, chama o pipeline e apresenta o resultado.
- `app/services/repository.py` valida imagens de cadastro, organiza os arquivos biométricos e lê/escreve os metadados JSON.
- `app/services/pipeline.py` executa as etapas de reconhecimento e salva as imagens de diagnóstico.
- `app/templates/` contém as páginas HTML; `app/static/css/` define a apresentação e `app/static/js/` controla a webcam e a captura no navegador.
- `scripts/setup_https.ps1` configura certificados locais para o HTTPS na rede.

O fluxo de autenticação é: aquisição da imagem → pré-processamento → detecção e recorte da face → extração de características → comparação com todos os perfis ativos → decisão pelo menor valor de distância e pelo limiar → apresentação do perfil e dos recursos demonstrativos associados ao nível.

## Pipeline de processamento

1. **Aquisição:** a imagem JPEG/PNG recebida é decodificada pelo OpenCV. A aplicação mantém uma cópia da imagem original para a tela de processamento.
2. **Pré-processamento:** a imagem é reduzida quando seu maior lado excede 900 pixels. O OpenCV aplica um filtro bilateral (`d=5`, `sigmaColor=25`, `sigmaSpace=25`) para suavizar ruídos e preservar contornos. Em seguida, converte a imagem para o espaço LAB e aplica CLAHE ao canal de luminosidade para realçar o contraste local. A mesma sequência é aplicada às imagens de referência antes de gerar seus encodings. A captura processada volta a BGR para exibição e é convertida a RGB para a biblioteca facial.
3. **Detecção/segmentação:** `face_recognition` usa o detector HOG do dlib para localizar as faces. O protótipo exige exatamente uma face; a região localizada é desenhada e salva como recorte facial.
4. **Extração:** dlib calcula um embedding facial numérico de 128 dimensões para representar as características da face.
5. **Comparação 1:N:** o embedding consultado é comparado com os embeddings das imagens de todos os usuários ativos. Quando um perfil tem várias imagens, usa-se a menor distância daquele perfil. Os candidatos são ordenados da menor para a maior distância.
6. **Decisão:** o candidato mais próximo é aceito se sua distância for menor ou igual a `0.60`. Distâncias menores indicam maior proximidade segundo a métrica do modelo; não são uma porcentagem de semelhança. Aumentar o limiar facilita aceitações e também pode aumentar falsos positivos.

A tela **Processamento da Imagem** mostra a imagem original, a imagem pré-processada, a detecção/segmentação, a sequência das etapas, uma amostra do embedding e a tabela de candidatos com suas distâncias e indicação em relação ao limiar.

## Níveis de acesso

- **Nível 1 — Padrão:** consulta de informações públicas e dados gerais.
- **Nível 2 — Avançado:** recursos do nível 1 e acesso aos relatórios de fiscalização, análises técnicas e ocorrências ambientais.
- **Nível 3 — Administrador:** recursos dos níveis anteriores e acesso a informações estratégicas e decisões administrativas.

No estado atual, esses recursos são apresentados condicionalmente na página de resultado. O servidor ainda não implementa contas autenticadas, sessões de usuário ou regras de autorização que bloqueiem páginas e operações por nível. Portanto, os níveis servem para demonstrar a interface, não para impor segurança.

## Bibliotecas e tecnologias

| Tecnologia | Uso no projeto |
|---|---|
| Python | Linguagem da aplicação e do processamento. |
| Flask | Servidor web, rotas, formulários e renderização HTML. |
| Werkzeug | Componentes HTTP usados pelo Flask e representação da imagem capturada no formulário. |
| OpenCV (`opencv-python` / `opencv-python-headless`) | Decodificação, redimensionamento, filtro bilateral, conversão de cores, CLAHE, marcação e gravação de imagens; a variante headless é usada no contêiner. |
| NumPy | Representação da imagem recebida como vetor de bytes para decodificação pelo OpenCV. |
| `face_recognition` | Interface de alto nível para detecção, encodings e distâncias faciais. |
| dlib e `face_recognition_models` | Detector HOG e modelo usado para gerar os embeddings faciais. |
| `qrcode[pil]` | Geração do QR code com o endereço da aplicação na rede. |
| HTML, CSS e JavaScript | Interface web responsiva e acesso à webcam pelo navegador (`getUserMedia`); o canvas reduz a imagem antes do envio. |
| JSON e sistema de arquivos | Persistência local dos perfis, imagens faciais e resultados de processamento. |
| `mkcert` | Criação de certificados HTTPS locais confiáveis nos dispositivos configurados. |

As dependências Python estão listadas em `requirements.txt`. Bibliotecas padrão como `json`, `pathlib`, `base64`, `uuid` e `socket` também são usadas para persistência, validação de imagem, identificação das capturas e descoberta do IP local.

## Armazenamento local

- `data/users.json`: lista de perfis com identificador, nome, nível de acesso, caminhos das imagens e estado ativo.
- `data/faces/<id-do-usuário>/`: imagens biométricas usadas como referência. O cadastro descarta arquivos inválidos e imagens que não contenham exatamente um rosto.
- `instance/captures/<id-da-captura>/`: imagem original, imagem pré-processada, imagem anotada, recorte facial (quando detectado) e `result.json` com etapas, candidatos e detalhes do resultado.
- `certs/`: certificado e chave do servidor, além do certificado público da autoridade local para configurar outros clientes.

As capturas de autenticação ficam armazenadas localmente e não há rotina automática de expurgo no protótipo. Faça cópias de segurança com cuidado e apague esses dados quando não forem mais necessários.

## Privacidade e limitações

Imagens faciais e embeddings são dados biométricos sensíveis. Neste protótipo, imagens de referência e resultados ficam no disco local sem criptografia própria; o servidor de desenvolvimento pode ser acessado pelos dispositivos da rede enquanto estiver ligado. Use somente dados de pessoas que autorizaram o uso, restrinja o acesso ao computador e à rede, não exponha a aplicação diretamente à internet e encerre o servidor com `Ctrl+C` ao terminar.

O sistema não implementa prova de vida, prevenção de ataques por fotografia/vídeo, proteção contra apresentação, autorização segura por função, trilha de auditoria ou avaliação formal de desempenho. A identificação pode falhar ou associar uma pessoa incorretamente; não use o protótipo para decisões reais de segurança.
