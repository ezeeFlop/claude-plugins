import { randomUUID } from 'node:crypto';

async function waitFor(promise, ms) {
  let timer;
  try { await Promise.race([promise, new Promise(resolve => { timer = setTimeout(resolve, ms); })]); }
  finally { clearTimeout(timer); }
}
export class Jobs {
  constructor() { this.jobs = new Map(); }

  async run(operation, work) {
    const now = Date.now();
    for (const [id, job] of this.jobs) if (job.finished_at && now - job.finished_at > 3600000) this.jobs.delete(id);
    if ([...this.jobs.values()].filter(job => job.status === 'running').length >= 4) throw new Error('Four operations are already running. Wait for an existing job before starting another.');
    if (this.jobs.size >= 200) {
      const oldest = [...this.jobs.values()].find(job => job.status !== 'running');
      if (oldest) this.jobs.delete(oldest.job_id);
    }
    const job = { job_id: randomUUID(), operation, status: 'running', started_at: now };
    this.jobs.set(job.job_id, job);
    job.promise = Promise.resolve().then(work).then(result => {
      job.status = 'completed'; job.result = result;
    }, error => {
      job.status = error.uncertain ? 'uncertain' : 'failed';
      job.error = error.message; job.http_status = error.status;
    }).finally(() => { job.finished_at = Date.now(); });
    await waitFor(job.promise, 300);
    return this.snapshot(job);
  }

  snapshot({ promise, ...job }) {
    return { ...job, ...(job.status === 'running' ? { next_step: 'Call codeur_job_status with this job_id. Do not start the operation again.' } : {}) };
  }

  async status(id, waitMs = 1000) {
    const job = this.jobs.get(id);
    if (!job) throw new Error('Unknown job (jobs belong to this connector process). After a restart, check the record in the application before retrying any write.');
    await waitFor(job.promise, waitMs);
    return this.snapshot(job);
  }
}
