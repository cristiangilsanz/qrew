// configures lint staged to fix and format files before commit
export default {
  '*.{ts,tsx}': ['eslint --fix', 'prettier --write'],
  '*.{json,md,css,html}': ['prettier --write'],
}
