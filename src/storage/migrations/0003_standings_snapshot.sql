-- standings_snapshot: histórico append-only da classificação (Princípio IV —
-- preservação de histórico). Sem constraint de unicidade de propósito: cada
-- coleta grava uma linha nova por time, nunca atualiza uma anterior.

CREATE TABLE IF NOT EXISTS standings_snapshot (
    id bigserial PRIMARY KEY,
    coletado_em timestamptz NOT NULL DEFAULT now(),
    phase_id uuid NOT NULL,
    team_id uuid NOT NULL REFERENCES teams (id),
    posicao integer NOT NULL,
    jogos integer NOT NULL,
    vitorias integer NOT NULL,
    derrotas integer NOT NULL,
    saldo_pontos integer NOT NULL,
    pontos_fiba numeric NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_standings_snapshot_phase_team ON standings_snapshot (phase_id, team_id, coletado_em);
