'use strict';

function main() {
  const chunks = [];
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', (chunk) => chunks.push(chunk));
  process.stdin.on('end', () => {
    try {
      const rows = JSON.parse(chunks.join(''));
      if (!Array.isArray(rows)) {
        throw new TypeError('Railway deployment list must be a JSON array');
      }

      const excludedIds = new Set(
        (process.argv[2] || '').split(',').filter(Boolean),
      );
      const releaseImage = normalizeImage(process.argv[3] || '');
      if (!releaseImage) {
        throw new TypeError('release image is required');
      }

      const deployment = rows.find((row) => {
        const id = typeof row?.id === 'string' ? row.id : '';
        return id && !excludedIds.has(id) && metadataHasReleaseImage(row.meta, releaseImage);
      });

      const id = typeof deployment?.id === 'string' ? deployment.id : '';
      const status = typeof deployment?.status === 'string' ? deployment.status : '';
      process.stdout.write(`${id}\t${status}\n`);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      process.stderr.write(`Unable to select Railway deployment: ${message}\n`);
      process.exitCode = 1;
    }
  });
}

function normalizeImage(value) {
  if (typeof value !== 'string') {
    return '';
  }
  const candidate = value.trim().replace(/^docker:\/\//, '');
  return candidate
    .replace(/^https:\/\/(?:index\.docker\.io\/v1|registry-1\.docker\.io|docker\.io)\//, '')
    .replace(/^(?:index\.docker\.io\/v1|registry-1\.docker\.io|docker\.io)\//, '');
}

function metadataHasReleaseImage(meta, releaseImage) {
  if (!meta || typeof meta !== 'object' || Array.isArray(meta)) {
    return false;
  }

  // Railway deployment metadata has emitted the Docker source at these two
  // explicit paths. Never recurse through arbitrary metadata: fields such as
  // buildMetadata.image are build annotations, not the deployed source.
  const candidates = [meta.image, meta.source?.image];
  return candidates.some(
    (candidate) => typeof candidate === 'string'
      && normalizeImage(candidate) === releaseImage,
  );
}

if (require.main === module) {
  main();
}

module.exports = { normalizeImage };
