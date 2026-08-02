-- Dimensões: teams, players (ver data-model.md)

CREATE TABLE IF NOT EXISTS teams (
    id uuid PRIMARY KEY,
    nome text NOT NULL,
    tri_code text NOT NULL,
    cor text,
    criado_em timestamptz NOT NULL DEFAULT now(),
    atualizado_em timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS players (
    id uuid PRIMARY KEY,
    nome text NOT NULL,
    team_id uuid NOT NULL REFERENCES teams (id),
    numero_camisa text,
    criado_em timestamptz NOT NULL DEFAULT now(),
    atualizado_em timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_players_team_id ON players (team_id);
