import { v4 as uuidv4 } from 'uuid';

/**
 * Create a prompt for learners to answer about a lesson resource.
 * @param {string} [text=''] - The question learners answer
 * @returns {{id: string, text: string}} The prompt, with a new id in hex form
 */
export function createPrompt(text = '') {
  return { id: uuidv4().replace(/-/g, ''), text };
}
