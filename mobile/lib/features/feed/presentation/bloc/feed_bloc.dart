import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:rental_property/features/feed/domain/feed_repository.dart';
import 'package:rental_property/features/feed/domain/property_summary.dart';

sealed class FeedEvent extends Equatable {
  const FeedEvent();

  @override
  List<Object?> get props => [];
}

final class FeedRequested extends FeedEvent {
  const FeedRequested({this.query});

  final String? query;

  @override
  List<Object?> get props => [query];
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
  const FeedLoaded(this.properties);

  final List<PropertySummary> properties;

  @override
  List<Object?> get props => [properties];
}

final class FeedEmpty extends FeedState {
  const FeedEmpty();
}

final class FeedFailure extends FeedState {
  const FeedFailure(this.message);

  final String message;

  @override
  List<Object?> get props => [message];
}

class FeedBloc extends Bloc<FeedEvent, FeedState> {
  FeedBloc(this._repository) : super(const FeedLoading()) {
    on<FeedRequested>(_onRequested);
  }

  final FeedRepository _repository;
  String _query = '';

  Future<void> _onRequested(FeedRequested event, Emitter<FeedState> emit) async {
    if (event.query != null) {
      _query = event.query!.trim();
    }

    emit(const FeedLoading());
    try {
      final properties = await _repository.fetchProperties(query: _query);
      if (properties.isEmpty) {
        emit(const FeedEmpty());
      } else {
        emit(FeedLoaded(properties));
      }
    } catch (_) {
      emit(const FeedFailure('Could not load rental listings. Please try again.'));
    }
  }
}
