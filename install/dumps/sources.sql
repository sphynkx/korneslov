INSERT INTO sources (code, lang, title, license, notes, canon_group, enabled)
VALUES
  ('SYNODAL', 'ru', 'Russian Synodal Translation (CSV)', 'Public Domain', NULL, 'protestant_66', 1),
  ('KJV',     'en', 'King James Version (CSV)',         'Public Domain', NULL, 'protestant_66', 1),
  ('WLC',     'he', 'Westminster Leningrad Codex (CSV)', 'Public Domain', NULL, 'protestant_66', 1)
ON DUPLICATE KEY UPDATE
  lang=VALUES(lang),
  title=VALUES(title),
  license=VALUES(license),
  notes=VALUES(notes),
  canon_group=VALUES(canon_group),
  enabled=VALUES(enabled);
