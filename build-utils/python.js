const { sync: commandExists } = require('command-exists');

const log = require('./log');


const runtimeBinaryMap = {
  'python3.9': 'python3.9',
};


async function findPythonBinary(runtime) {
  if (!(runtime in runtimeBinaryMap)) {
    throw new Error(`Unable to identify runtime (${runtime})`);
  }

  const binaryName = runtimeBinaryMap[runtime];
  if (commandExists(binaryName)) {
    log.info(`Found matching python (${binaryName})`);
    return binaryName;
  }

  throw new Error(`Unable to find binary ${binaryName} for runtime ${runtime}`);
}


function validateRuntime(runtime) {
  if (!(runtime in runtimeBinaryMap)) {
    log.error(`Invalid runtime configured (${runtime}). Available runtimes:`);
    Object.keys(runtimeBinaryMap).forEach((key) => {
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
