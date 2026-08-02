-- Fatos por partida: games, player_game_stats, team_game_stats (ver data-model.md)
--
-- Todas com chave de conflito no id externo do go-champs (Princípio I —
-- idempotência via upsert). `status` de games usa formas femininas
-- ("processada"/"cancelada") para concordar com "partida" — ver FR-018.

CREATE TABLE IF NOT EXISTS games (
    id uuid PRIMARY KEY,
    phase_id uuid NOT NULL,
    rodada_data date,
    time_casa_id uuid NOT NULL REFERENCES teams (id),
    time_visitante_id uuid NOT NULL REFERENCES teams (id),
    placar_casa integer,
    placar_visitante integer,
    status text NOT NULL DEFAULT 'processada' CHECK (status IN ('processada', 'cancelada')),
    is_finished_raw boolean,
    criado_em timestamptz NOT NULL DEFAULT now(),
    corrigido_em timestamptz
);

CREATE INDEX IF NOT EXISTS idx_games_phase_id ON games (phase_id);

CREATE TABLE IF NOT EXISTS player_game_stats (
    id uuid PRIMARY KEY,
    game_id uuid NOT NULL REFERENCES games (id),
    player_id uuid NOT NULL REFERENCES players (id),
    time_id_na_partida uuid NOT NULL REFERENCES teams (id),
    jogou boolean NOT NULL,
    minutos_jogados numeric,
    pontos integer NOT NULL,
    rebotes_ofensivos integer NOT NULL,
    rebotes_defensivos integer NOT NULL,
    assistencias integer NOT NULL,
    roubos integer NOT NULL,
    tocos integer NOT NULL,
    faltas_pessoais integer NOT NULL,
    faltas_tecnicas integer NOT NULL,
    faltas_antidesportivas integer NOT NULL,
    faltas_desqualificantes integer NOT NULL,
    faltas_desqualificantes_briga integer NOT NULL,
    faltas_flagrantes integer NOT NULL,
    faltas_desqualificantes_jogo integer NOT NULL,
    arremessos_2pt_tentados integer NOT NULL,
    arremessos_2pt_convertidos integer NOT NULL,
    arremessos_3pt_tentados integer NOT NULL,
    arremessos_3pt_convertidos integer NOT NULL,
    lances_livres_tentados integer NOT NULL,
    lances_livres_convertidos integer NOT NULL,
    turnovers integer NOT NULL,
    eficiencia numeric NOT NULL,
    plus_minus integer NOT NULL,
    criado_em timestamptz NOT NULL DEFAULT now(),
    corrigido_em timestamptz
);

CREATE INDEX IF NOT EXISTS idx_player_game_stats_game_id ON player_game_stats (game_id);
CREATE INDEX IF NOT EXISTS idx_player_game_stats_player_id ON player_game_stats (player_id);

CREATE TABLE IF NOT EXISTS team_game_stats (
    id uuid PRIMARY KEY,
    game_id uuid NOT NULL REFERENCES games (id),
    team_id uuid NOT NULL REFERENCES teams (id),
    vitoria boolean NOT NULL,
    saldo_pontos integer NOT NULL,
    fiba_group_points numeric,
    pontos integer NOT NULL,
    pontos_sofridos integer NOT NULL,
    arremessos_2pt_tentados integer NOT NULL,
    arremessos_2pt_convertidos integer NOT NULL,
    arremessos_3pt_tentados integer NOT NULL,
    arremessos_3pt_convertidos integer NOT NULL,
    lances_livres_tentados integer NOT NULL,
    lances_livres_convertidos integer NOT NULL,
    rebotes_ofensivos integer NOT NULL,
    rebotes_defensivos integer NOT NULL,
    assistencias integer NOT NULL,
    roubos integer NOT NULL,
    tocos integer NOT NULL,
    turnovers integer NOT NULL,
    faltas integer NOT NULL,
    eficiencia numeric NOT NULL,
    plus_minus integer NOT NULL,
    criado_em timestamptz NOT NULL DEFAULT now(),
    corrigido_em timestamptz
);

CREATE INDEX IF NOT EXISTS idx_team_game_stats_game_id ON team_game_stats (game_id);
CREATE INDEX IF NOT EXISTS idx_team_game_stats_team_id ON team_game_stats (team_id);
