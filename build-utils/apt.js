const path = require('path');
const execa = require('execa');

const log = require('./log');

async function install(packages, ...args) {
  log.subheading('Updating linux packages');
  log.info('Running "apt update"');
  try {
    const ret = await execa('apt', ['update']);
    log.info(ret.stdout);
  } catch (err) {
    log.error('Failed to run "apt update"');
    throw err;
  }
  log.subheading('Installing linux packages');
  log.info(`Running "apt install ${args.join(' ')} ${packages.join(' ')}"`);
  try {
    const ret = await execa('apt', ['install', ...args, ...packages]);
    log.info(ret.stdout);
  } catch (err) {
    log.error();
    throw err;
  }
}

function findRequirements(entrypoint, files) {
  log.subheading('Searching for "apt-requirements.txt"');

  const entryDirectory = path.dirname(entrypoint);
  const requirementsTxt = path.join(entryDirectory, 'apt-requirements.txt');

  if (files[requirementsTxt]) {
    log.info('Found local "apt-requirements.txt"');
    return files[requirementsTxt].fsPath;
  }

  if (files['apt-requirements.txt']) {
    log.info('Found global "apt-requirements.txt"');
    return files['apt-requirements.txt'].fsPath;
  }

  log.info('No "apt-requirements.txt" found');
  return null;
}

module.exports = {
  install, findRequirements,
};
