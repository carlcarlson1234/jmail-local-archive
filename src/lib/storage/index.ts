import { LocalStorageProvider } from './local';
import { StorageProvider } from './types';

export type { StorageProvider } from './types';
export { LocalStorageProvider } from './local';

export function createRawDataStorage(): StorageProvider {
  const basePath = process.env.RAW_DATA_ROOT || './data/raw/jmail';
  return new LocalStorageProvider(basePath);
}

export function createAssetStorage(): StorageProvider {
  const basePath = process.env.RAW_ASSETS_ROOT || './data/raw-assets';
  return new LocalStorageProvider(basePath);
}
