from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Author, Book, Member, Loan
from .serializers import AuthorSerializer, BookSerializer, MemberSerializer, LoanSerializer
from rest_framework.decorators import action
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination
from .tasks import send_loan_notification
from django.db.models import Count, F

class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer


class  setPag (PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page = 100
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.select_related('author').all()
    serializer_class = BookSerializer
    pagination_class = setPag


    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Example of conditional prefetching
        # If we need to include loans data for certain requests
        if self.request.query_params.get('include_loans', False):
            queryset = queryset.prefetch_related('loans')
            
        return queryset

    @action(detail=True, methods=['post'])
    def loan(self, request, pk=None):
        book = self.get_object()
        if book.available_copies < 1:
            return Response({'error': 'No available copies.'}, status=status.HTTP_400_BAD_REQUEST)
        member_id = request.data.get('member_id')
        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return Response({'error': 'Member does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        loan = Loan.objects.create(book=book, member=member)
        book.available_copies -= 1
        book.save()
        send_loan_notification.delay()
        return Response({'status': 'Book loaned successfully.'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def return_book(self, request, pk=None):
        book = self.get_object()
        member_id = request.data.get('member_id')
        try:
            loan = Loan.objects.get(book=book, member__id=member_id, is_returned=False)
        except Loan.DoesNotExist:
            return Response({'error': 'Active loan does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        loan.is_returned = True
        loan.return_date = timezone.now().date()
        loan.save()
        book.available_copies += 1
        book.save()
        return Response({'status': 'Book returned successfully.'}, status=status.HTTP_200_OK)

class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer

    @action(detail=False, methods=['get'])
    def top_active(self, request):
        top_members = Member.objects.annotate(
            active_loans=Count('loans', filter=F('loans__is_returned') == False)
        ).order_by('-active_loans')[:5]
        
        # Prepare response data
        result = []
        for member in top_members:
            result.append({
                'id': member.id,
                'username': member.user.username,
                'email': member.user.email,
                'active_loans': member.active_loans
            })
        
        return Response(result)

class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
    
    @action(detail=True, methods=['post'])
    def extend_due_date(self,request, pk=None):
        loan = self.get_object()
        addtional_days = request.data.get("additional_days",7)
        try:
             addtional_days = int(addtional_days)
             new_due_date =  loan.extend_due_date(addtional_days)
             serializer = self.get_serializer(loan)
             return Response({
                 "status": 'succces',
                 'message': f'Due date extended by {addtional_days} days new date {new_due_date}',
                 
             }, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({ 'status' : ' error','message' : str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

