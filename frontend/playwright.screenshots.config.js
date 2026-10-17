const baseConfig = require("./playwright.config");

module.exports = {
  ...baseConfig,
  testMatch: "**/readme-screenshots.spec.js",
  testIgnore: [],
};
