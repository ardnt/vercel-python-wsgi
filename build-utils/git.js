// const path = require('path');
const execa = require('execa');

const log = require('./log');

async function update(srcDir) {
  log.subheading('Updating submodules');
  log.info(`Running "git submodule update --git-dir ${srcDir} --init --recursive "`);
  try {
    const ret = await execa('git', ['submodule', 'update', '--git-dir', srcDir, '--init', '--recursive']);
    log.info(ret.stdout);
  } catch (err) {
    log.error();
    throw err;
  }
}

module.exports = {
  update,
};
