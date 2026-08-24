'use strict';

/**
 * Parse JSON string, check syntax.
 * @param {string} content 
 * @returns {{valid: boolean, errors: string[]}}
 */
const validateJson = (content) => {
    try {
        JSON.parse(content);
        return { valid: true, errors: [] };
    } catch (e) {
        return { valid: false, errors: [`Invalid JSON: ${e.message}`] };
    }
};

module.exports = validateJson;
