# RadioHub - Informacao Tecnica

Este manual explica os conceitos-chave, termos tecnicos e limitacoes do RadioHub. Ajuda-o a compreender porque certas funcionalidades funcionam da forma que funcionam.

---

## Modos de Reproducao

### Modo HLS (Predefinido)

HLS significa "HTTP Live Streaming". O RadioHub converte o fluxo de radio atraves do backend em pequenos segmentos que o navegador pode reproduzir. Isto permite:

- **Diferido (Timeshift):** Retroceder dentro do programa em curso
- **Pausa e Retoma:** O buffer continua em segundo plano
- **Gravacao de Buffer:** Gravar conteudo previamente ouvido (HLS-REC)
- **Controlo de Bitrate:** Adaptacao automatica a ligacao

O buffer HLS e mantido no backend. O tamanho pode ser configurado em [Definicoes > Geral](#/setup/allgemein/einstellungen) (Buffer de Diferido).

### Modo Direto

No modo Direto, o navegador liga-se diretamente ao fluxo original da estacao. Isto e mais eficiente em recursos, mas sem diferido, pausa ou gravacao de buffer. Util para servidores que nao suportam conversao HLS.

---

## Emblemas na Lista de Estacoes

### ICY (verde / cinzento)

**ICY** significa "Icecast Metadata" - um protocolo que permite as estacoes de radio enviar o titulo atual dentro do fluxo. Quando uma estacao suporta ICY, o RadioHub apresenta o titulo atual e pode dividir automaticamente as gravacoes em cancoes individuais.

- **ICY (verde, "bom"):** A estacao fornece marcas temporais precisas de mudanca de titulo. Os cortes serao limpos.
- **ICY (verde, "fraco"):** A estacao fornece dados ICY, mas as marcas temporais sao imprecisas (p. ex., reportes atrasados). Os cortes podem ter sobreposicoes ou lacunas.
- **ICY (cinzento):** ICY esta presente mas a qualidade ainda nao foi avaliada. Clique para alternar entre "bom" e "fraco".

**Porque e que isto importa?** Algumas estacoes reportam o novo titulo apenas segundos apos a mudanca real. O RadioHub usa posicoes de bytes no fluxo de audio para o calculo do corte, mas se a estacao reportar com atraso, o corte sera impreciso.

### Emblemas AD (Detecao de Anuncios)

O RadioHub pode verificar estacoes quanto a anuncios. A verificacao pode ser iniciada em [Setup > Radio > Estacoes](#/setup/radio/sender) e analisa URLs de fluxos e respostas de servidores:

- **0% AD (verde):** Sem suspeita de anuncios apos verificacao
- **XX% AD (amarelo):** Percentagem de suspeita (p. ex., "35% AD") - limiar configuravel
- **AD (vermelho):** Manualmente marcado como anuncio (oculto)
- **OK (azul):** Manualmente aprovado apesar da suspeita

---

## Sistema de Gravacao

### Gravacao Segmentada

O RadioHub grava em segmentos de 30 minutos. Se a ligacao a estacao cair, no maximo o segmento atual e perdido - nao a gravacao inteira. Para uma gravacao de 8 horas, isso seria no maximo 30 minutos em vez de tudo. Definicoes de gravacao (formato, bitrate, pasta) em [Setup > Gravacoes](#/setup/aufnahmen).

### Detecao de Paragem

Durante uma gravacao, o RadioHub monitoriza o tamanho do ficheiro. Se o ficheiro nao crescer durante 30 segundos, o processo de gravacao e detetado como "parado" e reiniciado. Isto previne gravacoes silenciosas onde o FFmpeg esta a correr mas ja nao recebe dados.

### Divisao por Titulo ICY

Se uma estacao tem metadados ICY, os segmentos de 30 minutos sao automaticamente divididos em cancoes individuais com base nas mudancas de titulo detetadas apos a gravacao. Sem ICY, os blocos de 30 minutos permanecem como segmentos.

### Fluxos HTTPS e Reconexao

Muitas estacoes usam HTTPS. A funcao de reconexao integrada do FFmpeg so funciona de forma fiavel com fluxos HTTP. Por isso, o RadioHub gere a monitorizacao e reinicio em quedas de ligacao por conta propria, independentemente do protocolo.

---

## Diferido e Buffer

### Como Funciona o Diferido?

O backend mantem um buffer rotativo de segmentos de audio. Cada segmento tem alguns segundos de duracao. O navegador solicita estes segmentos via lista de reproducao HLS. Ao retroceder, segmentos mais antigos sao carregados do buffer.

### Gravacao de Buffer (HLS-REC)

A gravacao de buffer utiliza o buffer HLS existente. Quando inicia uma gravacao, o RadioHub pode incluir os ultimos X minutos do buffer. O periodo de retrospetiva e configuravel em [Definicoes > Geral](#/setup/allgemein/einstellungen) (Gravacao HLS). Isto permite gravar uma cancao que ja esta a tocar.

---

## Cutter (Ferramenta de Edicao)

### Forma de Onda

A visualizacao da forma de onda e calculada a partir dos dados de audio (valores de pico). Mostra o volume ao longo do tempo e ajuda na colocacao precisa de pontos de corte.

### Marcadores

Marcadores sao pontos de corte na forma de onda. Podem ser definidos manualmente ou tomados automaticamente das mudancas de titulo ICY. Ao cortar, a gravacao e dividida nestes pontos em segmentos.

### Analise de Transicao

A analise examina as areas de audio em torno de cada marcador. Avalia se a transicao e limpa (silencio entre titulos) ou problematica (p. ex., crossfade onde dois titulos se sobrepoem). Cores: Verde = bom, Amarelo = verificar, Vermelho = problematico.

### Normalizacao (EBU R128)

A normalizacao ajusta o volume para o padrao EBU R128 - o padrao europeu de radiodifusao para volume consistente. Desta forma, todos os segmentos soam igualmente altos, independentemente do volume original da estacao.

---

## Sistema de Podcasts

### Transferencia Automatica

Podcasts subscritos podem transferir automaticamente novos episodios. O intervalo e configuravel em [Setup > Podcast](#/setup/podcast). As transferencias sao armazenadas localmente e ficam disponiveis offline.

### Atualizacao de Feed

Os feeds de podcasts sao consultados via RSS/Atom. O [intervalo de atualizacao](#/setup/podcast) determina com que frequencia o RadioHub verifica novos episodios.

---

## Armazenamento e Dados

Em [Setup > Armazenamento](#/setup/speicher), os caminhos de armazenamento para gravacoes, podcasts e cache podem ser configurados. A visualizacao mostra espaco utilizado e livre por zona.

Fontes de dados externas (Radio-Browser API, Podcast Index) sao visiveis em [Setup > Servicos](#/setup/dienste) e podem ser redirecionadas para instancias proprias se necessario.

---

## Processos Automaticos em Segundo Plano

O RadioHub executa varios processos em segundo plano que funcionam sem interacao do utilizador:

### Atualizacao de Feeds de Podcasts

Quando o RadioHub inicia, um processo periodico em segundo plano e lancado que verifica automaticamente todos os feeds de podcasts subscritos para novos episodios. O intervalo (predefinido: 6 horas) e configuravel em [Setup > Podcast](#/setup/podcast). Com a transferencia automatica ativada, novos episodios sao transferidos automaticamente.

### Gestao de Buffer HLS

Assim que uma estacao e reproduzida em modo HLS, o backend inicia um processo FFmpeg que divide o fluxo de audio em segmentos curtos (1 segundo cada). Estes formam um buffer rotativo de 10 minutos. Em paralelo, um registador de metadados ICY corre que deteta mudancas de titulo no fluxo. Ambos os processos terminam automaticamente quando a reproducao e parada.

### Monitorizacao de Gravacao

Durante uma gravacao ativa, dois processos de monitorizacao correm:

- **Detecao de Paragem:** A cada 30 segundos, verifica se o ficheiro de gravacao esta a crescer. Tres verificacoes consecutivas sem crescimento (90 segundos) acionam um reinicio do processo de gravacao.
- **Monitorizacao de Armazenamento:** O espaco livre em disco e verificado regularmente. Se cair abaixo de 100 MB, a gravacao e automaticamente parada para prevenir perda de dados.

### Gravacao de Buffer HLS (HLS-REC)

Durante uma gravacao de buffer HLS, um processo coletor copia novos segmentos do buffer HLS para o diretorio de gravacao a cada 0,5 segundos. No inicio, os minutos de retrospetiva configurados sao adicionalmente retirados do buffer existente. Na paragem, os segmentos sao automaticamente fundidos e divididos em titulos individuais se dados ICY estiverem disponiveis.

### Cache de Favicon

Ao carregar a lista de estacoes, icones de estacoes em falta sao transferidos em segundo plano e armazenados em cache localmente. Este processo corre silenciosamente e nao afeta a interface.

### Detecao de Bitrate

Ao reproduzir uma estacao pela primeira vez, o RadioHub verifica o bitrate real e o codec via FFprobe. O resultado e guardado e apresentado na lista de estacoes. Em [Setup > Radio > Estacoes](#/setup/radio/sender), uma verificacao em massa para todas as estacoes pode ser iniciada.

---

## Limitacoes Conhecidas

- **Diferido apenas em modo HLS:** Fluxos diretos sao passados 1:1, sem buffer.
- **Qualidade ICY varia:** Algumas estacoes fornecem metadados imprecisos ou atrasados. Isto afeta a precisao dos cortes.
- **Certificados SSL:** Algumas estacoes usam configuracoes SSL incomuns. O RadioHub contorna isto quando necessario, mas avisos podem ocorrer.
- **Gravacoes longas:** Durante quedas de ligacao, no maximo 30 minutos sao perdidos (um segmento). Segmentos mais antigos sao preservados.
- **Limitacoes do navegador:** A Web Audio API no navegador so pode fornecer dados do medidor VU quando o contexto de audio esta ativo. Alguns navegadores requerem interacao do utilizador para isto.

---

## Leitura Adicional

Para os curiosos tecnicamente - as tecnologias e padroes por detras do RadioHub:

### Protocolos de Streaming

- [HTTP Live Streaming (HLS)](https://pt.wikipedia.org/wiki/HTTP_Live_Streaming) - Protocolo de streaming adaptativo da Apple usado pelo RadioHub para diferido
- [Icecast](https://pt.wikipedia.org/wiki/Icecast) - Servidor de streaming open-source que popularizou o protocolo de metadados ICY
- [SHOUTcast / Protocolo ICY](https://pt.wikipedia.org/wiki/SHOUTcast) - Origem do padrao de metadados ICY para informacoes de titulo em fluxos
- [Radio pela Internet](https://pt.wikipedia.org/wiki/R%C3%A1dio_via_Internet) - Visao geral do streaming de radio na internet

### Formatos de Audio e Codecs

- [MP3 (MPEG-1 Audio Layer 3)](https://pt.wikipedia.org/wiki/MP3) - O formato de audio mais comum para fluxos de radio
- [AAC (Advanced Audio Coding)](https://pt.wikipedia.org/wiki/Advanced_Audio_Coding) - Codec mais moderno com melhor qualidade ao mesmo bitrate
- [Ogg Vorbis](https://pt.wikipedia.org/wiki/Vorbis) - Codec de audio livre e aberto
- [FLAC (Free Lossless Audio Codec)](https://pt.wikipedia.org/wiki/FLAC) - Compressao sem perdas para a mais alta qualidade

### Processamento de Audio

- [EBU R128](https://en.wikipedia.org/wiki/EBU_R_128) - Padrao europeu para normalizacao de volume em radiodifusao
- [FFmpeg](https://pt.wikipedia.org/wiki/FFmpeg) - O framework multimidia central usado pelo RadioHub para conversao, gravacao e corte
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API) - Interface do navegador para analise de audio (medidor VU, forma de onda)

### Fontes de Dados

- [Radio-Browser API](https://www.radio-browser.info/) - Base de dados comunitaria aberta com mais de 30.000 estacoes de radio em todo o mundo
- [Podcast Index](https://podcastindex.org/) - Catalogo aberto de podcasts como alternativa a diretorios proprietarios
- [RSS (Really Simple Syndication)](https://pt.wikipedia.org/wiki/RSS) - O formato de feed atraves do qual os podcasts disponibilizam novos episodios

### Fundamentos Tecnicos

- [Bitrate](https://pt.wikipedia.org/wiki/Taxa_de_bits) - Taxa de dados de um fluxo de audio (p. ex., 128 kbps, 320 kbps)
- [Streaming Media](https://pt.wikipedia.org/wiki/Streaming) - Fundamentos da transmissao de dados em tempo real
- [Compressao de Audio](https://pt.wikipedia.org/wiki/Codec_de_%C3%A1udio) - Como funciona a compressao com perdas
- [SSL/TLS](https://pt.wikipedia.org/wiki/Transport_Layer_Security) - Encriptacao usada em fluxos HTTPS
