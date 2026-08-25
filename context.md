  ### 📋 Resumo de Contexto: Projeto TuiPet / DragonPet

  1. Objetivo Principal e Arquitetura

  • Projeto: Um jogo de Pet Virtual de terminal (TUI) construído em Python, utilizando as bibliotecas Textual e Rich.
  • Objetivo Atual (O Pivot): Transformar o TuiPet em "DragonPet", expurgando 100% da propriedade intelectual (IP) de Digimon para evitar problemas de licenciamento e
  viabilizar a publicação comercial. O novo universo terá uma temática de fantasia medieval (ex: Ovo Ignis e dragões elementais baseados nos cuidados do jogador).
  • Branch Atual: expurgo_digimon (sincronizada com a main após revertermos uma tentativa de renomeação que quebrou os testes).

  2. O Que Já Foi Implementado e Está Funcionando

  • O motor do jogo é estável (todos os 2.699 testes automatizados estão passando).
  • Sistema global de internacionalização (i18n) implementado, incluindo correção de larguras de caracteres asiáticos (wcwidth) nos menus.
  • Documentação da API gerada via Pdoc e salva na pasta docs/api/.
  • Plano Mestre de migração de IP totalmente documentado em TODO/planejamento.md.
  • Correção recente do inicializador: o comando tuipet no terminal foi consertado no pyproject.toml e está abrindo o jogo corretamente.

  3. Decisões de Design e Tecnologia Tomadas

  • A Regra de Ouro (Paridade Código-Dado): Descobrimos a duras penas que o motor Python e os dados (.csv, .json, .wav) são siameses. Não podemos fazer um "Replace
  All" no código (ex: jogress -> fusion) sem antes limpar e sincronizar os CSVs, senão o jogo colapsa.
  • Fase 1 - A Poda: Antes de renomear as lógicas do motor, vamos podar as 1.500 linhas de monstros da Bandai nos arquivos CSV, reduzindo para uma árvore enxuta de
  ~20 dragões originais.
  • Bug de Tradução da Loja (A Observação Importante): Vimos que a loja tem itens em inglês (ex: Fish, hunger +1). Isso ocorre porque há textos hardcoded no arquivo
  catalog.py e o carregador dos CSVs ignora as colunas de idioma nativas. Decisão: Não vamos perder tempo consertando a tradução de 1.500 itens inúteis da Bandai. Em
  vez disso, vamos deletar tudo na Poda (Fase 1), e então aplicaremos a função inteligente t() apenas nos nossos novos itens medievais definitivos.
 
  • Nova Tecnologia Visual: Planejamento para refatorar o anim.py, migrando da renderização atual de 16x16 (usando meios-blocos ▀) para a tecnologia de matriz Braille,
  dobrando a resolução para 32x32 e permitindo sprites medievais mais detalhados no terminal.

  4. Proxima Tarefa na fila a ser executada
  
  • Executar a FASE 1: A Poda Geral.
  • Arquivos Alvo: src/tuipet/data/monster.csv, lines.csv e foods.csv.
  • Ação: Apagar as 1.500 linhas de Digimons e comidas atuais. Criar o nosso Ovo Ignis e mapear os 20 primeiros dragões e comidas medievais para substituir a massa de
  dados atual.



