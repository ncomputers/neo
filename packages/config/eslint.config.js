import js from '@eslint/js';
import ts from 'typescript-eslint';
import react from 'eslint-plugin-react';

export default ts.config(
  js.configs.recommended,
  react.configs.recommended,
  {
    files: ['**/*.{ts,tsx,js}'],
    ignores: ['dist']
  }
);
