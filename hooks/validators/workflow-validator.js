'use strict';

const { STAGES, STAGE_INDEX } = require('../utils/config.js');

/**
 * Verify the target stage is the next legal stage.
 * @param {string} currentStage 
 * @param {string} targetStage 
 * @returns {{valid: boolean, errors: string[]}}
 */
const validateStageOrder = (currentStage, targetStage) => {
    const errors = [];
    const currentIndex = STAGE_INDEX[currentStage];
    const targetIndex = STAGE_INDEX[targetStage];
    
    if (currentIndex === undefined) {
        errors.push(`Unknown current stage: ${currentStage}`);
    }
    if (targetIndex === undefined) {
        errors.push(`Unknown target stage: ${targetStage}`);
    }
    
    if (errors.length === 0) {
        if (targetIndex !== currentIndex + 1 && targetIndex !== currentIndex) {
            errors.push(`Target stage ${targetStage} is not the next legal stage from ${currentStage}`);
        }
    }
    
    return { valid: errors.length === 0, errors };
};

/**
 * Verify that all stages before target are completed.
 * @param {string[]} completedStages 
 * @param {string} targetStage 
 * @returns {{valid: boolean, errors: string[]}}
 */
const validateNoSkippedStages = (completedStages, targetStage) => {
    const errors = [];
    const targetIndex = STAGE_INDEX[targetStage];
    
    if (targetIndex === undefined) {
        errors.push(`Unknown target stage: ${targetStage}`);
        return { valid: false, errors };
    }
    
    for (let i = 0; i < targetIndex; i++) {
        const stage = STAGES[i];
        if (!completedStages.includes(stage)) {
            errors.push(`Required previous stage not completed: ${stage}`);
        }
    }
    
    return { valid: errors.length === 0, errors };
};

module.exports = { validateStageOrder, validateNoSkippedStages };
