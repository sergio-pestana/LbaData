-- Escopo por torneio em teams/players (feature 002 — múltiplos torneios).
--
-- `teams`/`players` não tinham nenhuma coluna de escopo até aqui porque cada
-- uma vinha embutida no payload de um único torneio por vez (research.md #2
-- de specs/002-add-series-2025-2026); com múltiplos torneios simultâneos,
-- `tournament_id` é necessário para `storage/reads.py` conseguir filtrar por
-- torneio. `id` continua sendo a chave primária (sem chave composta) — não há
-- evidência de colisão de id entre torneios diferentes (ver research.md #2).
--
-- Aditiva e sem perda de dado (Princípio IV): a coluna é adicionada como
-- nullable, as linhas já existentes do Ouro 2026 (única temporada coletada
-- antes desta feature) são preenchidas por UPDATE, e só depois a coluna vira
-- NOT NULL. Reexecutar esta migration não falha nem duplica nada (Princípio I
-- — mesma idempotência de toda migration deste projeto).

ALTER TABLE teams ADD COLUMN IF NOT EXISTS tournament_id uuid;
ALTER TABLE players ADD COLUMN IF NOT EXISTS tournament_id uuid;

UPDATE teams SET tournament_id = '5bf23f0b-6768-46ec-bcc1-4cd698105413'
    WHERE tournament_id IS NULL;
UPDATE players SET tournament_id = '5bf23f0b-6768-46ec-bcc1-4cd698105413'
    WHERE tournament_id IS NULL;

ALTER TABLE teams ALTER COLUMN tournament_id SET NOT NULL;
ALTER TABLE players ALTER COLUMN tournament_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_teams_tournament_id ON teams (tournament_id);
CREATE INDEX IF NOT EXISTS idx_players_tournament_id ON players (tournament_id);
