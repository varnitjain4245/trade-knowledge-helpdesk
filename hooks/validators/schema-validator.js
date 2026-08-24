'use strict';

/**
 * Verify required fields exist for project json.
 * @param {Object} obj 
 * @returns {{valid: boolean, errors: string[]}}
 */
const validateProjectJson = (obj) => {
    const errors = [];
    if (!obj || typeof obj !== 'object') {
        return { valid: false, errors: ['Input must be a valid object'] };
    }
    
    const requiredFields = ['workflow', 'status', 'current_stage', 'completed_stages', 'stages'];
    requiredFields.forEach(field => {
        if (!(field in obj)) errors.push(`Missing required field: ${field}`);
    });
    
    if (obj.stages && typeof obj.stages === 'object') {
        const expectedStages = ['requirement', 'prd_review', 'hld', 'hld_review', 'lld', 'lld_review', 'planning', 'implementation', 'review', 'test'];
        expectedStages.forEach(stage => {
            if (!(stage in obj.stages)) {
                errors.push(`Missing stage key in stages: ${stage}`);
            } else {
                const stageObj = obj.stages[stage];
                if (stageObj) {
                    ['status', 'verified', 'artifact', 'errors'].forEach(req => {
                        if (!(req in stageObj)) {
                            errors.push(`Stage ${stage} missing required field: ${req}`);
                        }
                    });
                }
            }
        });
    }

    return { valid: errors.length === 0, errors };
};

/**
 * Verify required fields exist for workflow state.
 * @param {Object} obj 
 * @returns {{valid: boolean, errors: string[]}}
 */
const validateWorkflowState = (obj) => {
    const errors = [];
    if (!obj || typeof obj !== 'object') {
        return { valid: false, errors: ['Input must be a valid object'] };
    }
    
    const requiredFields = ['currentStage', 'workflowStatus', 'iteration', 'approvedStages', 'rejectedStages', 'staleArtifacts', 'lastUpdated', 'artifactVersions'];
    requiredFields.forEach(field => {
        if (!(field in obj)) errors.push(`Missing required field: ${field}`);
    });

    return { valid: errors.length === 0, errors };
};

module.exports = { validateProjectJson, validateWorkflowState };
