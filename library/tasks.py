from celery import shared_task
from .models import Loan
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

@shared_task
def send_loan_notification(loan_id):
    try:
        loan = Loan.objects.get(id=loan_id)
        member_email = loan.member.user.email
        book_title = loan.book.title
        send_mail(
            subject='Book Loaned Successfully',
            message=f'Hello {loan.member.user.username},\n\nYou have successfully loaned "{book_title}".\nPlease return it by the due date.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[member_email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error in send_loan_notification: {e}")
        raise


@shared_task
def check_overdue_loans():

    today = timezone.now().date()
    over_due_loans = Loan.objects.filter(due_date__lt=today,is_returned = False).select_related('book','member__user')
    notification_count = 0
    for loan in over_due_loans:
        days_overdue = (today - loan.due_date).days

        subject = f"Overdue Book: '{loan.book.title}'"
        message = f"""   
        Dear '{loan.member.user.username}',

        Our record shows that the book '{loan.book.title}' is overdue by  {days_overdue} day(s).
        The book was due on {loan.due_date}.
        please return the book  to the library 
        """
    send_mail(
         subject=subject,
         message=message,
         from_email=settings.DEFAULT_FROM_EMAIL,
          recipient_list=[loan.member.user.email],
         fail_silently=False

    )
    notification_count +=1
    return f"Sent {notification_count} overdue notifications"