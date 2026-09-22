import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:rental_property/features/feed/domain/feed_filters.dart';
import 'package:rental_property/features/feed/domain/feed_repository.dart';
import 'package:rental_property/features/feed/domain/property_summary.dart';

sealed class FeedEvent extends Equatable {
  const FeedEvent();

  @override
  List<Object?> get props => [];
}

final class FeedRequested extends FeedEvent {
  const FeedRequested({this.query, this.filters});

  final String? query;
  final FeedFilters? filters;

  @override
  List<Object?> get props => [query, filters];
}

sealed class FeedState extends Equatable {
  const FeedState();

  @override
  List<Object?> get props => [];
}

final class FeedLoading extends FeedState {
  const FeedLoading();
}

final class FeedLoaded extends FeedState {
  const FeedLoaded(this.properties, {required this.filters});

  final List<PropertySummary> properties;
  final FeedFilters filters;

  @override
  List<Object?> get props => [properties, filters];
}

final class FeedEmpty extends FeedState {
  const FeedEmpty({required this.filters});

  final FeedFilters filters;

  @override
  List<Object?> get props => [filters];
}

final class FeedFailure extends FeedState {
  const FeedFailure(this.message, {required this.filters});

  final String message;
  final FeedFilters filters;

  @override
  List<Object?> get props => [message, filters];
}

class FeedBloc extends Bloc<FeedEvent, FeedState> {
  FeedBloc(this._repository) : super(const FeedLoading()) {
    on<FeedRequested>(_onRequested);
  }

  final FeedRepository _repository;
  String _query = '';
  FeedFilters _filters = const FeedFilters();

  FeedFilters get filters => _filters;

  Future<void> _onRequested(FeedRequested event, Emitter<FeedState> emit) async {
    if (event.query != null) {
      _query = event.query!.trim();
    }
    if (event.filters != null) {
      _filters = event.filters!;
    }

    emit(const FeedLoading());
    try {
      final properties = await _repository.fetchProperties(
        query: _query,
        filters: _filters,
      );
      if (properties.isEmpty) {
        emit(FeedEmpty(filters: _filters));
      } else {
        emit(FeedLoaded(properties, filters: _filters));
      }
    } catch (_) {
      emit(FeedFailure(
        'Could not load rental listings. Please try again.',
        filters: _filters,
      ));
    }
  }
}
