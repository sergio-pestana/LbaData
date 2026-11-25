-- Chave natural nas tabelas de fato por partida.
--
-- A fonte (go-champs) às vezes reemite o registro de estatística de uma súmula
-- corrigida com um `id` novo. Como o upsert casava só por `id`, a correção
-- entrava como uma segunda linha para o mesmo (jogo, time) — o jogo passava a
-- contar em dobro nas médias. Encontrado em 25/11/2026: 6 pares duplicados em
-- team_game_stats (Ouro 2026 e Bronze 2026), nenhum em player_game_stats.
--
-- 1. Remove as duplicatas mantendo a linha mais recente (a da súmula corrigida;
--    conferido contra a soma das estatísticas dos jogadores).
-- 2. Garante uma linha por (jogo, time) e por (jogo, jogador) com índice único,
--    que o upsert usa como alvo do ON CONFLICT.
-- Idempotente: na segunda execução o DELETE não acha nada e os índices já existem.

DELETE FROM team_game_stats t
USING team_game_stats newer
WHERE newer.game_id = t.game_id
  AND newer.team_id = t.team_id
  AND (newer.criado_em, newer.id) > (t.criado_em, t.id);

DELETE FROM player_game_stats p
USING player_game_stats newer
WHERE newer.game_id = p.game_id
  AND newer.player_id = p.player_id
  AND (newer.criado_em, newer.id) > (p.criado_em, p.id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_team_game_stats_game_team
    ON team_game_stats (game_id, team_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_player_game_stats_game_player
    ON player_game_stats (game_id, player_id);
