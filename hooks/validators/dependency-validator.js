'use strict';

const { DEPENDENCY_CHAIN } = require('../utils/config.js');

/**
 * Given an artifact name, check that all upstream artifacts in the dependency chain are NOT stale.
 * @param {string} artifactName 
 * @param {Object} artifactVersions 
 * @returns {{valid: boolean, errors: string[]}}
 */
const validateDependenciesFresh = (artifactName, artifactVersions) => {
    const errors = [];
    const index = DEPENDENCY_CHAIN.indexOf(artifactName);
    
    if (index === -1) {
        errors.push(`Unknown artifact: ${artifactName}`);
        return { valid: false, errors };
    }
    
    for (let i = 0; i < index; i++) {
        const upstream = DEPENDENCY_CHAIN[i];
        const metadata = artifactVersions[upstream];
        
        if (!metadata) {
            errors.push(`Upstream artifact missing: ${upstream}`);
        } else if (metadata.approvalStatus === 'stale') {
            errors.push(`Upstream artifact is stale: ${upstream}`);
        }
    }
    
    return { valid: errors.length === 0, errors };
};

module.exports = validateDependenciesFresh;
