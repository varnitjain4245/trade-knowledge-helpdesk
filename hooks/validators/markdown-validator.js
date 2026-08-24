'use strict';

/**
 * Check that the markdown content contains all required heading strings.
 * @param {string} content 
 * @param {string[]} requiredHeadings 
 * @returns {{valid: boolean, errors: string[]}}
 */
const validateMarkdownStructure = (content, requiredHeadings = []) => {
    const errors = [];
    
    if (typeof content !== 'string') {
        return { valid: false, errors: ['Content must be a string'] };
    }
    
    // Look for lines starting with #
    const lines = content.split('\n');
    const headingLines = lines.filter(line => line.trim().startsWith('#'));
    
    for (const req of requiredHeadings) {
        const found = headingLines.some(line => line.includes(req));
        if (!found) {
            errors.push(`Missing required heading: ${req}`);
        }
    }
    
    return { valid: errors.length === 0, errors };
};

module.exports = validateMarkdownStructure;
