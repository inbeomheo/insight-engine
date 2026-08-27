'use strict';

const { normalizeImage } = require('./select_railway_deployment.cjs');

const chunks = [];
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => chunks.push(chunk));
process.stdin.on('end', () => {
  try {
    const payload = JSON.parse(chunks.join(''));
    const mode = process.argv[2] || '';

    if (mode === 'select-service') {
      selectService(payload, process.argv[3] || '');
      return;
    }
    if (mode === 'validate-environment') {
      validateEnvironment(
        payload,
        process.argv[3] || '',
        process.argv[4] || '',
      );
      return;
    }
    if (mode === 'validate-settings') {
      validateEnvironment(payload, process.argv[3] || '', null);
      return;
    }
    if (mode === 'select-public-origin') {
      selectPublicOrigin(payload);
      return;
    }
    throw new TypeError(`unknown Railway contract mode: ${mode || '(empty)'}`);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    process.stderr.write(`Railway live contract validation failed: ${message}\n`);
    process.exitCode = 1;
  }
});

function selectService(payload, serviceName) {
  if (!serviceName) {
    throw new TypeError('service name is required');
  }
  const edges = payload?.services?.edges;
  if (!Array.isArray(edges)) {
    throw new TypeError('Railway status is missing services.edges');
  }
  const matches = edges
    .map((edge) => edge?.node)
    .filter((node) => node?.name === serviceName && typeof node?.id === 'string' && node.id);
  if (matches.length !== 1) {
    throw new TypeError(`expected exactly one service named ${serviceName}, found ${matches.length}`);
  }
  process.stdout.write(`${matches[0].id}\n`);
}

function validateEnvironment(payload, serviceId, releaseImageValue) {
  if (!serviceId) {
    throw new TypeError('service id is required');
  }
  const releaseImage = releaseImageValue === null
    ? null
    : normalizeImage(releaseImageValue);
  if (releaseImageValue !== null && !releaseImage) {
    throw new TypeError('release image is required');
  }
  const services = payload?.services;
  if (!services || typeof services !== 'object' || Array.isArray(services)) {
    throw new TypeError('Railway environment config is missing services');
  }
  const service = Object.prototype.hasOwnProperty.call(services, serviceId)
    ? services[serviceId]
    : null;
  if (
    !service
    || typeof service !== 'object'
    || Array.isArray(service)
    || service.isDeleted === true
    || service.isCreated === false
  ) {
    throw new TypeError(`active service ${serviceId} is missing from Railway environment config`);
  }

  const sourceImage = normalizeImage(service.source?.image || '');
  if (!sourceImage || service.source?.repo) {
    throw new TypeError('live service must use a Docker image source');
  }
  if (releaseImage !== null && sourceImage !== releaseImage) {
    throw new TypeError('live service source is not the exact release image');
  }

  const deploy = service.deploy;
  if (!deploy || typeof deploy !== 'object') {
    throw new TypeError('live service deploy config is missing');
  }
  if (deploy.healthcheckPath !== '/ready') {
    throw new TypeError('live healthcheckPath must be /ready');
  }
  if (!Number.isFinite(deploy.healthcheckTimeout) || deploy.healthcheckTimeout < 120) {
    throw new TypeError('live healthcheckTimeout must be at least 120 seconds');
  }
  if (deploy.requiredMountPath !== '/app/persist') {
    throw new TypeError('live requiredMountPath must be /app/persist');
  }
  if (!Number.isFinite(deploy.drainingSeconds) || deploy.drainingSeconds < 630) {
    throw new TypeError('live drainingSeconds must be at least 630 seconds');
  }

  const volumeMounts = service.volumeMounts;
  if (!volumeMounts || typeof volumeMounts !== 'object' || Array.isArray(volumeMounts)) {
    throw new TypeError('live service volume mounts are missing');
  }
  const mountEntries = Object.entries(volumeMounts);
  if (
    mountEntries.length !== 1
    || !mountEntries[0][1]
    || typeof mountEntries[0][1] !== 'object'
    || Array.isArray(mountEntries[0][1])
    || mountEntries[0][1].mountPath !== '/app/persist'
  ) {
    throw new TypeError('live service must have exactly one volume mounted at /app/persist');
  }

  const [volumeId] = mountEntries[0];
  const volumes = payload?.volumes;
  if (!volumes || typeof volumes !== 'object' || Array.isArray(volumes)) {
    throw new TypeError('Railway environment config is missing top-level volumes');
  }
  const volume = Object.prototype.hasOwnProperty.call(volumes, volumeId)
    ? volumes[volumeId]
    : null;
  if (
    !volume
    || typeof volume !== 'object'
    || Array.isArray(volume)
    || volume.isCreated !== true
    || volume.isDeleted === true
  ) {
    throw new TypeError(`mounted volume ${volumeId} is missing or inactive`);
  }

  process.stdout.write(`Railway live contract verified for service ${serviceId}\n`);
}

function selectPublicOrigin(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new TypeError('Railway variables must be a JSON object');
  }
  const rawOrigin = payload.PUBLIC_ORIGIN;
  if (typeof rawOrigin !== 'string' || !rawOrigin.trim()) {
    throw new TypeError('PUBLIC_ORIGIN is missing');
  }
  let origin;
  try {
    origin = new URL(rawOrigin.trim());
  } catch {
    throw new TypeError('PUBLIC_ORIGIN must be a valid URL');
  }
  if (
    origin.protocol !== 'https:'
    || origin.username
    || origin.password
    || origin.pathname !== '/'
    || origin.search
    || origin.hash
    || !origin.hostname
  ) {
    throw new TypeError('PUBLIC_ORIGIN must be a pathless HTTPS origin');
  }
  const runtimeDrainSeconds = Number(payload.RAILWAY_DEPLOYMENT_DRAINING_SECONDS);
  if (!Number.isFinite(runtimeDrainSeconds) || runtimeDrainSeconds < 630) {
    throw new TypeError(
      'RAILWAY_DEPLOYMENT_DRAINING_SECONDS must be at least 630',
    );
  }
  process.stdout.write(`${origin.origin}\n`);
}
