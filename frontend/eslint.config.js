import js from "@eslint/js"
import globals from "globals"
import reactHooks from "eslint-plugin-react-hooks"
import reactRefresh from "eslint-plugin-react-refresh"
import tseslint from "typescript-eslint"
import importX from "eslint-plugin-import-x"
import checkFile from "eslint-plugin-check-file"
import { createTypeScriptImportResolver } from "eslint-import-resolver-typescript"
import { defineConfig, globalIgnores } from "eslint/config"

export default defineConfig([
  globalIgnores(["dist"]),
  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
    rules: {
      "react-refresh/only-export-components": "off",
    },
  },
  // Bulletproof React's rules (.eslintrc.cjs), with eslint-plugin-import-x in place of eslint-plugin-import,
  // which doesn't support ESLint 10
  {
    files: ["src/**/*.{ts,tsx}"],
    plugins: { "import-x": importX, "check-file": checkFile },
    settings: {
      "import-x/resolver-next": [
        createTypeScriptImportResolver({ project: "./tsconfig.app.json" }),
      ],
    },
    rules: {
      // Features don't import from each other, and imports run from shared code to features to the app
      // (docs/project-structure.md)
      "import-x/no-restricted-paths": [
        "error",
        {
          zones: [
            {
              target: "./src/features/courses",
              from: "./src/features",
              except: ["./courses"],
            },
            {
              target: "./src/features/learning",
              from: "./src/features",
              except: ["./learning"],
            },
            { target: "./src/features", from: "./src/app" },
            {
              target: [
                "./src/components",
                "./src/config",
                "./src/lib",
                "./src/types",
                "./src/utils",
              ],
              from: ["./src/features", "./src/app"],
            },
          ],
        },
      ],
      // docs/project-standards.md
      "check-file/filename-naming-convention": [
        "error",
        { "**/*.{ts,tsx}": "KEBAB_CASE" },
        { ignoreMiddleExtensions: true },
      ],
    },
  },
  {
    files: ["src/**/*"],
    plugins: { "check-file": checkFile },
    rules: {
      "check-file/folder-naming-convention": [
        "error",
        { "**/*": "KEBAB_CASE" },
      ],
    },
  },
])
