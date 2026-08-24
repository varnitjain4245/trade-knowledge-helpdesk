'use strict';

const { SKILL_MAP } = require('../utils/config.js');

/**
 * Check if the skill is in the allowed list for that stage.
 * @param {string} stage 
 * @param {string} skillName 
 * @returns {{valid: boolean, errors: string[]}}
 */
const validateSkillForStage = (stage, skillName) => {
    const errors = [];
    const allowedSkills = SKILL_MAP[stage];
    
    if (!allowedSkills) {
        errors.push(`Unknown stage: ${stage}`);
        return { valid: false, errors };
    }
    
    if (!allowedSkills.includes(skillName)) {
        errors.push(`Skill ${skillName} is not allowed for stage ${stage}`);
    }
    
    return { valid: errors.length === 0, errors };
};

module.exports = validateSkillForStage;
