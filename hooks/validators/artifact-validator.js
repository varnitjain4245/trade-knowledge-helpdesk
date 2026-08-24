'use strict';

const { ARTIFACT_OWNER, VALID_APPROVAL_STATUSES } = require('../utils/config.js');

/**
 * Verify the artifact belongs to the current stage.
 * @param {string} artifactName 
 * @param {string} currentStage 
 * @returns {{valid: boolean, errors: string[]}}
 */
const validateArtifactOwnership = (artifactName, currentStage) => {
    const errors = [];
    const owner = ARTIFACT_OWNER[artifactName];
    
    if (!owner) {
        errors.push(`Unknown artifact: ${artifactName}`);
    } else if (owner !== currentStage) {
        errors.push(`Artifact ${artifactName} belongs to stage ${owner}, not ${currentStage}`);
    }
    
    return { valid: errors.length === 0, errors };
};

/**
 * Check version, createdAt, updatedAt, stage, status, checksum, lastModifiedBySkill, approvalStatus are present.
 * @param {Object} metadata 
 * @returns {{valid: boolean, errors: string[]}}
 */
const validateArtifactMetadata = (metadata) => {
    const errors = [];
    if (!metadata || typeof metadata !== 'object') {
        return { valid: false, errors: ['Metadata must be a valid object'] };
    }
    
    const requiredFields = ['version', 'createdAt', 'updatedAt', 'stage', 'status', 'checksum', 'lastModifiedBySkill', 'approvalStatus'];
    requiredFields.forEach(field => {
        if (!(field in metadata)) {
            errors.push(`Missing required metadata field: ${field}`);
        }
    });
    
    if (metadata.approvalStatus && !VALID_APPROVAL_STATUSES.includes(metadata.approvalStatus)) {
        errors.push(`Invalid approval status: ${metadata.approvalStatus}`);
    }
    
    return { valid: errors.length === 0, errors };
};

module.exports = { validateArtifactOwnership, validateArtifactMetadata };
