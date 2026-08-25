# Plano de Expurgo de IP (Fase 1) - TuiPet para DragonPet (5 Ovos Iniciais)

Como o motor do jogo possui a estrutura das 5 versões originais (ver1 até ver5) mapeadas no banco de dados matemático, nós **podemos usar todas as cinco** para criar 5 linhagens biológicas 100% independentes no DragonPet!

Ao invés de apagar as 1.500 linhas e deixar apenas 1 ovo, vamos apagar as 1.500 linhas e criar **5 ecossistemas completos**, mantendo o jogo enorme, porém 100% livre de licenças!

## 🥚 Os 5 Ovos Iniciais

### 1. Ovo Ignis (Árvore `ver1`) - Linhagem dos Dragões
Focado em Répteis Mágicos, Fogo e Terra.
*   **Bom Cuidado:** Filhote de Salamandra -> Dragão Nobre, Dragão Ancião.
*   **Mau Cuidado:** Filhote de Wyvern -> Basilisco Vulcânico, Dragão do Pântano.

### 2. Ovo Abissal (Árvore `ver2`) - Linhagem Marinha
Focado em Água, Krakens e Leviatãs.
*   **Bom Cuidado:** Girino Abissal -> Kraken das Profundezas.
*   **Mau Cuidado:** Filhote de Enguia -> Serpente Marinha, Sapo Pestilento.

### 3. Ovo Silvestre (Árvore `ver3`) - Linhagem das Feras & Quimeras
Focado em Feras Míticas, Bestas e Quimeras da floresta.
*   **Bom Cuidado:** Lobo Místico -> Grifo de Batalha, Manticora, Behemoth.
*   **Mau Cuidado:** Duende/Kobold -> Orc Selvagem, Lobisomem degenerado, Porco da Lama (peste).

### 4. Ovo de Âmbar (Árvore `ver4`) - Linhagem da Natureza & Construtos
Focado em Plantas Mágicas, Elementais e Golens (ver4 original era focado em plantas/vento).
*   **Bom Cuidado:** Mandrágora -> Ent (Árvore Viva), Golem de Pedra, Titã de Cristal.
*   **Mau Cuidado:** Semente Podre -> Espantalho Amaldiçoado, Golem de Barro (peste).

### 5. Ovo Amaldiçoado (Árvore `ver5`) - Linhagem dos Mortos-Vivos
Focado em Necromancia e Trevas (ver5 original era focada em monstros sombrios/osso).
*   **Bom Cuidado:** Fogo Fátuo -> Esqueleto Guerreiro, Cavaleiro da Morte, Lich Supremo.
*   **Mau Cuidado:** Caveira Quebrada -> Zumbi, Carniçal, Slime de Carne (peste).

---

## 🥩 Comidas e Itens (Unificados para todos)
Todos os 5 ovos se alimentarão do mesmo ecossistema de itens (afeta fome e energia, mas não muda a espécie):
1. **Javali Assado** (Carne)
2. **Lula Gigante** (Peixe)
3. **Fruto de Coral** (Fruta)
4. **Alga Ancestral** (Vegetal)
5. **Poção de Cura** (Remédio)
6. **Elixir do Abismo** (Vitamina)
7. **Torta de Ovas Mágicas** (Bolo)
8. **Cristal de Sal Doce** (Candy)
9. **Carne de Megalodonte** (Bife Especial)

## O Próximo Passo Mágico (Poda Geral)
Quando a execução da Fase 1 começar, deveremos varrer os 3 arquivos CSVs (`monster.csv`, `lines.csv`, `foods.csv`), deletar os ~1.450 monstros não utilizados, e inserir a base (ID, Nomes, Tipos) para essas 5 árvores (totalizando cerca de 85 monstros autorais).
