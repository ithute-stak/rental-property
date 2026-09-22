import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:rental_property/features/feed/domain/property_summary.dart';

sealed class FeedEvent extends Equatable {
  const FeedEvent();

  @override
  List<Object?> get props => [];
}

final class FeedRequested extends FeedEvent {
  const FeedRequested();
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
  FeedBloc() : super(const FeedLoading()) {
    on<FeedRequested>(_onRequested);
  }

  Future<void> _onRequested(FeedRequested event, Emitter<FeedState> emit) async {
    emit(const FeedLoading());

    // Temporary presentation seed. The next slice replaces this with the FastAPI repository.
    await Future<void>.delayed(const Duration(milliseconds: 250));
    emit(
      const FeedLoaded([
        PropertySummary(
          id: 'seed-1',
          title: 'Modern room in Maseru',
          area: 'Khubetsoana',
          town: 'Maseru',
          monthlyRent: 1800,
          availableRooms: 2,
          securityLevel: 'Enhanced',
          imageUrl: '',
        ),
        PropertySummary(
          id: 'seed-2',
          title: 'Quiet rooms near town',
          area: 'Ha Matala',
          town: 'Maseru',
          monthlyRent: 1500,
          availableRooms: 1,
          securityLevel: 'Standard',
          imageUrl: '',
        ),
      ]),
    );
  }
}
