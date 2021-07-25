const path = require('path');
const execa = require('execa');

const log = require('./log');

async function install(scriptPath) {
  log.subheading('Running setup script');
  log.info(`Running "bash ${scriptPath}"`);
  try {
    const ret = await execa('bash', [scriptPath]);
    log.info(ret.stdout);
  } catch (err) {
    log.error();
    throw err;
  }
}

function findRequirements(entrypoint, files) {
  log.subheading('Searching for "setup.sh"');

  const entryDirectory = path.dirname(entrypoint);
  const requirementsTxt = path.join(entryDirectory, 'setup.sh');

  if (files[requirementsTxt]) {
    log.info('Found local "setup.sh"');
    return files[requirementsTxt].fsPath;
  }

  if (files['setup.sh']) {
    log.info('Found global "setup.sh"');
    return files['setup.sh'].fsPath;
  }

  log.info('No "setup.sh" found');
  return null;
}

module.exports = {
  install, findRequirements,
};

function findPostRequirements(entrypoint, files) {
  log.subheading('Searching for "post-setup.sh"');

  const entryDirectory = path.dirname(entrypoint);
  const requirementsTxt = path.join(entryDirectory, 'post-setup.sh');

  if (files[requirementsTxt]) {
    log.info('Found local "post-setup.sh"');
    return files[requirementsTxt].fsPath;
  }

  if (files['post-setup.sh']) {
    log.info('Found global "post-setup.sh"');
    return files['post-setup.sh'].fsPath;
  }

  log.info('No "post-setup.sh" found');
  return null;
}

module.exports = {
  install, findRequirements, findPostRequirements,
};
