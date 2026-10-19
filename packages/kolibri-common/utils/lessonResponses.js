import { v4 as uuidv4 } from 'uuid';

/**
 * Create a prompt for learners to answer about a lesson resource.
 * @param {string} [text=''] - The question learners answer
 * @returns {{id: string, text: string}} The prompt, with a new id in hex form
 */
export function createPrompt(text = '') {
  return { id: uuidv4().replace(/-/g, ''), text };
}

/**
 * Whether a coach's entry is the address of a page on the web, which learners' browsers
 * can open: http or https only, as the server allows.
 * @param {string} value - What the coach entered
 * @returns {boolean} Whether it is a web address
 */
export function isWebAddress(value) {
  try {
    return ['http:', 'https:'].includes(new URL(value).protocol);
  } catch (error) {
    return false;
  }
}
