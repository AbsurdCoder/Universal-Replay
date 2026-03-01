import { Injectable } from '@angular/core';
import { signalStore, withState, withComputed, withMethods, patchState } from '@ngrx/signals';
import { computed } from '@angular/core';
import { TopicMetadata } from '../models/topic.model';

interface TopicState {
  topics: string[];
  selectedTopic: TopicMetadata | null;
  loading: boolean;
  error: string | null;
}

const initialState: TopicState = {
  topics: [],
  selectedTopic: null,
  loading: false,
  error: null,
};

/**
 * Kafka topic state store using NgRx Signals
 * Manages all topic related state
 */
@Injectable({
  providedIn: 'root',
})
export class TopicStore extends signalStore(
  withState(initialState),
  withComputed(({ topics, selectedTopic }) => ({
    topicCount: computed(() => topics().length),
    hasTopics: computed(() => topics().length > 0),
    selectedTopicName: computed(() => selectedTopic()?.name),
    selectedTopicPartitionCount: computed(() => selectedTopic()?.partitions.length ?? 0),
  })),
  withMethods((store) => ({
    setTopics(topics: string[]): void {
      patchState(store, { topics });
    },

    setSelectedTopic(topic: TopicMetadata | null): void {
      patchState(store, { selectedTopic: topic });
    },

    setLoading(loading: boolean): void {
      patchState(store, { loading });
    },

    setError(error: string | null): void {
      patchState(store, { error });
    },

    clearError(): void {
      patchState(store, { error: null });
    },

    reset(): void {
      patchState(store, initialState);
    },
  }))
) {
  constructor() {
    super();
  }
}
