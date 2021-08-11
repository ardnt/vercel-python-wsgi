const { sync: commandExists } = require('command-exists');

const log = require('./log');


const runtimeBinaryMap = [
  'python2.7',
  'python3.6',
  'python3.7',
  'python3.8',
];


async function findPythonBinary(runtime) {
  if (!runtimeBinaryMap.includes(runtime)) {
    throw new Error(`Unable to identify runtime (${runtime})`);
  }

  const binaryName = runtime;
  if (commandExists(binaryName)) {
    log.info(`Found matching python (${binaryName})`);
    return binaryName;
  }

  throw new Error(`Unable to find binary ${binaryName} for runtime ${runtime}`);
}


function validateRuntime(runtime) {
  if (!runtimeBinaryMap.includes(runtime)) {
    log.error(`Invalid runtime configured (${runtime}). Available runtimes:`);
    runtimeBinaryMap.forEach((key) => {
      log.error(` - ${key}`);
    });
    log.error('See Vercel runtime documentation for more information:');
    log.error('https://github.com/vercel/vercel/blob/main/DEVELOPING_A_RUNTIME.md#lambdaruntime');
    throw new Error(`Invalid runtime configured (${runtime}).`);
  }
  return true;
}


module.exports = {
  validateRuntime,
  findPythonBinary,
};
