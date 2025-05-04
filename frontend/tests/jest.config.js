// frontend/tests/jest.config.js
// Jest configuration file

module.exports = {
    testEnvironment: 'jsdom', // Simulate a browser environment
    setupFilesAfterEnv: ['<rootDir>/tests/setupTests.js'], // Run setup file after Jest environment is set up
    moduleNameMapper: {
        // Map CSS/other non-JS files to mocks
        '\\.(css|less|sass|scss)$': 'identity-obj-proxy',
        '\\.(gif|ttf|eot|svg|png)$': '<rootDir>/tests/__mocks__/fileMock.js',
    },
    transform: {
        '^.+\\.(js|jsx|ts|tsx)$': 'babel-jest', // Use babel-jest for JS/JSX/TS/TSX files
    },
    // Optional: coverage settings
    // collectCoverage: true,
    // collectCoverageFrom: ['<rootDir>/src/**/*.{js,jsx,ts,tsx}'],
    // coverageDirectory: 'coverage',
};
