'use strict';

const { VALID_TRANSITIONS } = require('../utils/config.js');

/**
 * Check if the transition is legal per VALID_TRANSITIONS.
 * @param {string} currentStatus 
 * @param {string} newStatus 
 * @returns {{valid: boolean, errors: string[]}}
 */
const validateStatusTransition = (currentStatus, newStatus) => {
    const errors = [];
    const allowed = VALID_TRANSITIONS[currentStatus];
    
    if (!allowed) {
        errors.push(`Unknown current status: ${currentStatus}`);
        return { valid: false, errors };
    }
    
    if (!allowed.includes(newStatus)) {
        errors.push(`Invalid transition from ${currentStatus} to ${newStatus}`);
    }
    
    return { valid: errors.length === 0, errors };
};

module.exports = validateStatusTransition;
