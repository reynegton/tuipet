# DragonPet (Nome Provisório): Documento de Rebranding e Planejamento

Este documento detalha o plano de guerra para extirpar a Propriedade Intelectual (IP) de "Digimon" do código-fonte e transformá-lo em um jogo autoral de Fantasia Medieval. O foco é manter o brilhante e complexo motor matemático original, substituindo toda a camada visual e narrativa.

## FASE 1: A Poda e Limpeza Profunda (Expurgo de IP)
* [ ] **Limpeza de Nomenclatura Global:** Varrer todo o repositório (código e arquivos de tradução `.json`) para remover termos patenteados.
  * `Digitama` -> `Ovo Místico`
  * `Jogress` -> `Fusão Arcana`
  * `DigiCore` -> `Núcleo de Mana`
  * `Digimon` -> `Familiar / Monstro / Criatura`
* [ ] **Limpeza de Arte (Sprites):** Deletar o arquivo `sprites.json.gz` (arte ripada) quando o novo gerador estiver pronto.
* [ ] **Poda das Tabelas de Dados (A Grande Limpeza do CSV):** 
  * Reduzir o colossal `monster.csv` (1.500 linhas) para apenas **~20 monstros iniciais**.
  * Faremos o "Replace 1-para-1" baseando-nos na árvore matemática da Versão 1 do brinquedo clássico, garantindo que as estatísticas de probabilidade, peso e fome continuem perfeitas, mas os nomes e elementos sejam os nossos.

## FASE 2: Novo Design Evolutivo (Coerência Biológica)
Diferente da lógica confusa original (cachorro que vira anjo), nosso universo terá evolução coerente. As falhas do jogador (Erros de cuidado, superalimentação, sujeira) causarão *Mutações Adaptativas* no monstro, alterando seu elemento base.

**Estudo de Caso do MVP: A Árvore do "Ovo Ignis" (Fogo)**
* **Fase 1 (Bebê):** `Faísca Mágica` (Apenas uma luz flutuante de mana pura).
* **Fase 2 (Treinamento):** `Brasa Viva` (Ganhou corpo, agora é uma bolinha de fogo com olhos).
* **Fase 3 (Novato - Base):** `Filhote de Salamandra` (Um pequeno bípede com escamas vermelhas).
* **Fase 4 (O Desvio de Cuidado):** O jogo ramifica aqui de forma narrativa:
  * *(Cuidado Perfeito - 0 Erros):* `Dragão Nobre` (Elemento Fogo/Luz). Alcança o ápice majestoso da espécie.
  * *(Cuidado Padrão - Poucos Erros):* `Wyvern de Fogo` (Elemento Fogo/Ar). Fica um pouco mais selvagem, cresce asas focadas em caça aérea.
  * *(Gordo e Preguiçoso - Comida demais, zero treino):* `Basilisco Vulcânico` (Elemento Fogo/Terra). Fica muito pesado, perde as asas, rasteja soltando lava e veneno fraco.
  * *(Extrema Negligência - Tela cheia de sujeira e doença):* `Dragão do Pântano` (Elemento Veneno/Trevas). A sujeira apagou sua chama interna. Ele sofreu mutação, começou a apodrecer e agora cospe ácido em vez de fogo.

## FASE 3: Engenharia Visual e Alta Resolução
* [ ] **O Problema da Resolução:** O jogo atual renderiza em "quadrados grandes" (Blocos Unicode ▀) para simular um LCD de 16x16 pixels.
* [ ] **A Solução (Renderização em Braille):** Reescrever a lógica do arquivo `anim.py` para utilizar matrizes de caracteres Braille (⠶). 
* [ ] **O Benefício:** O Braille contém 8 "pontos" de luz (2x4) na mesma área física de 1 letra do terminal. Isso permite quadruplicar a resolução (indo para 32x32 pixels visuais ou mais) mantendo o mascote pequeno e com altíssimo nível de detalhe (escamas, garras finas), o que é ideal para o design de Dragões.

## FASE 4: Criação da Nova Arte
* [ ] Desenhar (via Pixel Art ou IA conectada aos nossos scripts) a nossa folha de *sprites* (Spritesheet) para os novos monstros listados na FASE 2.
* [ ] As animações padrão exigidas pelo motor (11 quadros) deverão ser desenhadas: Idle, Andar, Comer, Dormir, Doente, Recusar, etc.
* [ ] Empacotar os novos monstros através do nosso próprio `extract_sprites.py` modificado.
