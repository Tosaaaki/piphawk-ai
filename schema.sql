-- === 運用系テーブル ===
CREATE TABLE IF NOT EXISTS trades (
    id            INTEGER PRIMARY KEY,
    ticket        TEXT    NOT NULL,
    side          TEXT    NOT NULL,
    entry_time    TEXT    NOT NULL,
    exit_time     TEXT,
    pl            REAL,
    pips          REAL
);

CREATE TABLE IF NOT EXISTS positions (
    id         INTEGER PRIMARY KEY,
    ticket     TEXT    NOT NULL,
    side       TEXT    NOT NULL,
    open_time  TEXT    NOT NULL,
    lot        REAL    NOT NULL
);

-- === Offline RL 学習用 ===
CREATE TABLE IF NOT EXISTS policy_transitions (
    id          INTEGER PRIMARY KEY,
    state       TEXT    NOT NULL,
    action      TEXT    NOT NULL,
    reward      REAL    NOT NULL,
    next_state  TEXT    NOT NULL,
    done        INTEGER NOT NULL
);

-- === Optuna チューニング用 ===
CREATE TABLE IF NOT EXISTS optuna_studies (
    study_name     TEXT    NOT NULL,
    trial_number   INTEGER NOT NULL,
    params_json    TEXT    NOT NULL,
    value          REAL,
    PRIMARY KEY (study_name, trial_number)
);
