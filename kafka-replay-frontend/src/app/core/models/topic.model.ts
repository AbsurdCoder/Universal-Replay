/**
 * Kafka topic models matching backend schemas
 */

export interface PartitionMetadata {
  partition_id: number;
  leader: number;
  replicas: number[];
  in_sync_replicas: number[];
}

export interface OffsetRange {
  earliest: number;
  latest: number;
  lag: number;
}

export interface TopicMetadata {
  name: string;
  partitions: PartitionMetadata[];
  replication_factor: number;
  offset_ranges: OffsetRange[];
  message_count: number;
  size_bytes: number;
}

export interface TopicListResponse {
  topics: string[];
  count: number;
}

export interface KafkaMessage {
  offset: number;
  partition: number;
  timestamp: number;
  key?: string;
  value: string;
  headers?: Record<string, string>;
}
