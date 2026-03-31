export interface StorageProvider {
  read(path: string): Promise<Buffer>;
  readStream(path: string): Promise<NodeJS.ReadableStream>;
  write(path: string, data: Buffer | string): Promise<void>;
  exists(path: string): Promise<boolean>;
  list(prefix: string): Promise<string[]>;
  delete(path: string): Promise<void>;
  getUrl(path: string): string;
  getAbsolutePath(path: string): string;
}

export interface StorageConfig {
  provider: 'local' | 's3' | 'r2';
  basePath: string;
}
