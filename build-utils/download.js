const { createWriteStream } = require('fs');
const fetch = require('node-fetch');
const path = require('path');

const getWritableDirectory = require('@vercel/build-utils/fs/get-writable-directory'); // eslint-disable-line import/no-extraneous-dependencies


async function file(url, fileName) {
  const res = await fetch(url);

  if (!res.ok || res.status !== 200) {
    throw new Error(`Failed to download "${url}"`);
  }

  const dir = await getWritableDirectory();
  const filePath = path.join(dir, fileName);
  const writeStream = createWriteStream(filePath);

  return new Promise((resolve, reject) => {
    res.body
      .on('error', reject)
      .pipe(writeStream)
      .on('finish', () => resolve(filePath));
  });
}


module.exports = { file };
