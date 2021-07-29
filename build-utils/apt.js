const path = require('path');
const execa = require('execa');

const log = require('./log');

async function install(scriptPath, srcDir) {
  log.subheading('Running install script');
  log.info(`Running "bash ${scriptPath} ${srcDir}"`);
  try {
    const ret = await execa('bash', [scriptPath, srcDir]);
    log.info(ret.stdout);
  } catch (err) {
    log.error();
    throw err;
  }
}

function findRequirements(entrypoint, files) {
  log.subheading('Searching for "install.sh"');

  const entryDirectory = path.dirname(entrypoint);
  const requirementsTxt = path.join(entryDirectory, 'install.sh');

  if (files[requirementsTxt]) {
    log.info('Found local "install.sh"');
    return files[requirementsTxt].fsPath;
  }

  if (files['install.sh']) {
    log.info('Found global "install.sh"');
    return files['install.sh'].fsPath;
  }

  log.info('No "install.sh" found');
  return null;
}

module.exports = {
  install, findRequirements,
};

function findPostRequirements(entrypoint, files) {
  log.subheading('Searching for "post-install.sh"');

  const entryDirectory = path.dirname(entrypoint);
  const requirementsTxt = path.join(entryDirectory, 'post-install.sh');

  if (files[requirementsTxt]) {
    log.info('Found local "post-install.sh"');
    return files[requirementsTxt].fsPath;
  }

  if (files['post-install.sh']) {
    log.info('Found global "post-install.sh"');
    return files['post-install.sh'].fsPath;
  }

  log.info('No "post-install.sh" found');
  return null;
}

module.exports = {
  install, findRequirements, findPostRequirements,
};
