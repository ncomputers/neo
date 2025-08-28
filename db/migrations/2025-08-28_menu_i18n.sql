-- Menu and outlet i18n support
ALTER TABLE menu_items
  ADD COLUMN IF NOT EXISTS name_i18n JSONB DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS desc_i18n JSONB DEFAULT NULL;

ALTER TABLE outlets
  ADD COLUMN IF NOT EXISTS default_lang TEXT DEFAULT 'en',
  ADD COLUMN IF NOT EXISTS enabled_langs TEXT[] DEFAULT ARRAY['en'];

UPDATE outlets SET default_lang='en' WHERE default_lang IS NULL;
