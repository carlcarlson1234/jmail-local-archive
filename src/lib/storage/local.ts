import * as fs from 'fs';
import * as path from 'path';
import { StorageProvider } from './types';

export class LocalStorageProvider implements StorageProvider {
  private basePath: string;

  constructor(basePath: string) {
    this.basePath = path.resolve(basePath);
  }

  async read(filePath: string): Promise<Buffer> {
    const fullPath = path.join(this.basePath, filePath);
    return fs.promises.readFile(fullPath);
  }

  async readStream(filePath: string): Promise<NodeJS.ReadableStream> {
    const fullPath = path.join(this.basePath, filePath);
    return fs.createReadStream(fullPath);
  }

  async write(filePath: string, data: Buffer | string): Promise<void> {
    const fullPath = path.join(this.basePath, filePath);
    await fs.promises.mkdir(path.dirname(fullPath), { recursive: true });
    await fs.promises.writeFile(fullPath, data);
  }

  async exists(filePath: string): Promise<boolean> {
    const fullPath = path.join(this.basePath, filePath);
    try {
      await fs.promises.access(fullPath);
      return true;
    } catch {
      return false;
    }
  }

  async list(prefix: string): Promise<string[]> {
    const fullPath = path.join(this.basePath, prefix);
    try {
      const entries = await fs.promises.readdir(fullPath, { recursive: true });
      return entries.map((e) => (typeof e === 'string' ? e : e.toString()));
    } catch {
      return [];
    }
  }

  async delete(filePath: string): Promise<void> {
    const fullPath = path.join(this.basePath, filePath);
    await fs.promises.unlink(fullPath);
  }

  getUrl(filePath: string): string {
    return `file://${path.join(this.basePath, filePath)}`;
  }

  getAbsolutePath(filePath: string): string {
    return path.join(this.basePath, filePath);
  }
}
