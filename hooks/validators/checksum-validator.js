'use strict';

const { hashFile } = require('../utils/checksum.js');

/**
 * Read the file, compute SHA-256, compare with expected.
 * @param {string} filePath 
 * @param {string} expectedChecksum 
 * @returns {{valid: boolean, errors: string[]}}
 */
const validateChecksum = (filePath, expectedChecksum) => {
    const errors = [];
    
    try {
        const actual = hashFile(filePath);
        if (actual === null) {
            errors.push(`Could not compute checksum for file: ${filePath}`);
        } else if (actual !== expectedChecksum) {
            errors.push(`Checksum mismatch. Expected ${expectedChecksum}, got ${actual}`);
        }
    } catch (e) {
        errors.push(`Error computing checksum: ${e.message}`);
    }
    
    return { valid: errors.length === 0, errors };
};

module.exports = validateChecksum;
