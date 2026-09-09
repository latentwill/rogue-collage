import type { Job, Layer, Project } from './types';

/** Searchable names come from the actual generation request, never its image URL. */
export function generatedAssetName(job: Job): string {
 const prompt = typeof job.params?.prompt === 'string' ? job.params.prompt.replace(/\s+/g, ' ').trim() : '';
 if (prompt) return prompt.length > 90 ? `${prompt.slice(0, 89).trimEnd()}…` : prompt;
 const action = job.operation.replace(/[-_]/g, ' ');
 return `${action.charAt(0).toUpperCase()}${action.slice(1)} · ${job.preset || job.id.slice(0, 6)}`;
}

function jobForLayer(layer: Layer): Job | undefined {
 if (layer.generation) return layer.generation;
 const provenance = (layer as Layer & { provenance?: { job?: Job } }).provenance;
 return provenance?.job;
}

/** Preserve artist-renamed assets; upgrade only the old automatic labels. */
export function migrateGeneratedAssetNames(project: Project): Project {
 let changed = false;
 const rename = (layer: Layer): Layer => {
  const job = jobForLayer(layer);
  if (!job) return layer;
  const generic = /^(?:generate[- ]piece|generate[- ]composition|generated (?:image|piece|result)|cutout|remove background|upscale)(?:\s*[·#-].*)?$/i.test(layer.name.trim()) || layer.name === job.operation;
  if (!generic) return layer;
  const name = generatedAssetName(job);
  if (name === layer.name) return layer;
  changed = true;
  return { ...layer, name };
 };
 const layers = project.layers.map(rename);
 const snippets = project.snippets?.map(rename);
 return changed ? { ...project, layers, snippets } : project;
}
