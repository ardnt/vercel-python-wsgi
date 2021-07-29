const path = require('path');
const execa = require('execa');

const download = require('./download');
const log = require('./log');

const url = 'https://bootstrap.pypa.io/get-pip.py';


async function install(pipPath, srcDir, ...args) {
  log.subheading('Installing python packages');
  log.info(`Running "pip install -t --recurse-submodules -j4 ${srcDir} ${args.join(' ')}"`);
  try {
    const ret = await execa(pipPath, ['install', '-t', srcDir, ...args]);
    await execa(pipPath, ['uninstall', 'dataclasses', '-y']);
    log.info(ret.stdout);
  } catch (err) {
    log.error(`Failed to run "pip install -t ${srcDir} ${args.join(' ')}"`);
    throw err;
  }
}


async function downloadAndInstallPip(pythonBin) {
  log.subheading('Installing pip');

  if (!process.env.PYTHONUSERBASE) {
    throw new Error(
      'Could not install "pip": "PYTHONUSERBASE" env var is not set',
    );
  }
  const getPipFilePath = await download.file(url, 'get-pip.py');

  log.info(`Running "${pythonBin} get-pip.py"`);
  try {
    const ret = await execa(pythonBin, [getPipFilePath, '--user']);
    log.info(ret.stdout);
  } catch (err) {
    log.error('Could not install pip');
    throw err;
  }
  return path.join(process.env.PYTHONUSERBASE, 'bin', 'pip');
}


function findRequirements(entrypoint, files) {
  log.subheading('Searching for "requirements.txt"');

  const entryDirectory = path.dirname(entrypoint);
  const requirementsTxt = path.join(entryDirectory, 'requirements.txt');

  if (files[requirementsTxt]) {
    log.info('Found local "requirements.txt"');
    return files[requirementsTxt].fsPath;
  }

  if (files['requirements.txt']) {
    log.info('Found global "requirements.txt"');
    return files['requirements.txt'].fsPath;
  }

  log.info('No "requirements.txt" found');
  return null;
}


module.exports = {
  install, downloadAndInstallPip, findRequirements,
};
