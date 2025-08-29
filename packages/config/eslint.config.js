import js from '@eslint/js';
import reactPlugin from 'eslint-plugin-react';
import globals from 'globals';

export default [
  js.configs.recommended,
  {
    plugins: {
      react: reactPlugin,
    },
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.es2021,
        ...globals.jest,
      },
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
    files: ['**/*.{js,jsx}'],
    ignores: ['dist'],
    rules: {
      ...reactPlugin.configs.recommended.rules,
      'react/react-in-jsx-scope': 'off',
      'react/prop-types': 'off',
      'react/no-unescaped-entities': 'off',
      'no-unused-vars': 'off',
      'no-empty': 'off',
      'no-undef': 'off',
    },
  },
];
