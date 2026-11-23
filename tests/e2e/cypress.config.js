const { defineConfig } = require("cypress");

module.exports = defineConfig({
  e2e: {
    baseUrl: "http://localhost:3000",
    specPattern: "./e2e/**/*.cy.{js,jsx,ts,tsx}",
    supportFile: "./support/e2e.js",
    fixturesFolder: "./fixtures",
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
  },
});
