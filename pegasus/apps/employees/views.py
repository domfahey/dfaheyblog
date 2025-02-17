from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Sum
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.templatetags.static import static
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.helpers import get_user_from_request
from apps.api.permissions import IsAuthenticatedOrHasUserAPIKey

from .forms import EmployeeForm
from .models import Employee
from .serializers import AggregateEmployeeDataSerializer, EmployeeSerializer


@login_required
def employee_list(request):
    return render(
        request,
        "pegasus/employees/list_employees.html",
        {"active_tab": "object_lifecycle", "employees": Employee.objects.filter(user=request.user)},
    )


@login_required
def new_employee(request):
    return _add_edit_employee(request)


@login_required
def edit_employee(request, employee_id):
    # don't forget to filter by user, else you'll allow people to edit other people's employees!
    employee = get_object_or_404(Employee, user=request.user, id=employee_id)
    return _add_edit_employee(request, employee)


def _add_edit_employee(request, employee: Employee = None):
    if employee:
        assert employee.user == request.user
    if request.method == "POST":
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            employee = form.save(commit=False)
            employee.user = request.user
            employee.save()
            return HttpResponseRedirect(reverse("pegasus_employees:django_object_lifecycle"))
    else:
        form = EmployeeForm(instance=employee)

    return render(
        request,
        "pegasus/employees/edit_employee.html",
        {
            "active_tab": "object_lifecycle",
            "employee": employee,
            "form": form,
        },
    )


@require_POST
@login_required
def delete_employee(request, employee_id):
    employee = get_object_or_404(Employee, user=request.user, id=employee_id)
    employee.delete()
    return HttpResponseRedirect(reverse("pegasus_employees:django_object_lifecycle"))


@login_required
def employee_list_htmx(request):
    return render(
        request,
        "pegasus/employees/htmx_object_lifecycle.html",
        {"active_tab": "object_lifecycle", "employees": Employee.objects.filter(user=request.user)},
    )


@login_required
def new_employee_row_htmx(request):
    return _add_edit_employee_htmx(request)


@login_required
def edit_employee_row_htmx(request, employee_id):
    employee = get_object_or_404(Employee, user=request.user, id=employee_id)
    return _add_edit_employee_htmx(request, employee)


def _add_edit_employee_htmx(request, employee=None):
    if request.method == "POST":
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            employee = form.save(commit=False)
            employee.user = request.user
            employee.save()
            return HttpResponseRedirect(reverse("pegasus_employees:htmx_get_employee", args=[employee.id]))
    else:
        form = EmployeeForm(instance=employee)

    return render(
        request,
        "pegasus/employees/htmx/edit_employee_row.html",
        {
            "employee": employee,
            "form": form,
        },
    )


def empty_htmx(request):
    return HttpResponse("")


@login_required
def get_employee_row_htmx(request, employee_id):
    employee = get_object_or_404(Employee, user=request.user, id=employee_id)
    return render(
        request,
        "pegasus/employees/htmx/employee_row.html",
        {
            "employee": employee,
        },
    )


@require_http_methods(["DELETE"])
@login_required
def delete_employee_htmx(request, employee_id):
    employee = get_object_or_404(Employee, user=request.user, id=employee_id)
    employee.delete()
    return HttpResponse("")


@method_decorator(login_required, name="dispatch")
class ObjectLifecycleView(TemplateView):
    def get_context_data(self, **kwargs):
        return {
            "active_tab": "object_lifecycle",
            "department_choices": [{"id": c[0], "name": c[1]} for c in Employee.DEPARTMENT_CHOICES],
        }


class ReactObjectLifecycleView(ObjectLifecycleView):
    template_name = "pegasus/employees/react_object_lifecycle.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "framework_url": "https://reactjs.org/",
                "framework_name": "React",
                "framework_icon": static("images/pegasus/react-icon.png"),
                "url_base": reverse("pegasus_employees:react_object_lifecycle"),
            }
        )
        return context


class VueObjectLifecycleView(ObjectLifecycleView):
    template_name = "pegasus/employees/vue_object_lifecycle.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "framework_url": "https://vuejs.org/",
                "framework_name": "Vue.js",
                "framework_icon": static("images/pegasus/vue-icon.png"),
                "url_base": reverse("pegasus_employees:vue_object_lifecycle"),
            }
        )
        return context


@method_decorator(login_required, name="dispatch")
class ChartsView(TemplateView):
    template_name = "pegasus/employees/charts.html"

    def get_context_data(self, **kwargs):
        return {
            "active_tab": "charts",
        }


class EmployeeDataAPIView(APIView):
    permission_classes = (IsAuthenticatedOrHasUserAPIKey,)

    @extend_schema(operation_id="employees_aggregate_data", responses={200: AggregateEmployeeDataSerializer})
    def get(self, request):
        user = get_user_from_request(request)
        data = user.employees.values("department").annotate(
            average_salary=Avg("salary"),
            total_cost=Sum("salary"),
            number_employees=Count("pk"),
        )
        # data will look something like this:
        # [
        #     {'total_cost': 132000, 'number_employees': 2, 'average_salary': 66000.0, 'department': 'hr'},
        #     {'total_cost': 60000, 'number_employees': 1, 'average_salary': 60000.0, 'department': 'marketing'}
        # ]
        total_costs = [[row["department"], row["total_cost"]] for row in data]
        average_salaries = [[row["department"], row["average_salary"]] for row in data]
        headcounts = [[row["department"], row["number_employees"]] for row in data]
        return Response(
            {
                "total_costs": total_costs,
                "average_salaries": average_salaries,
                "headcounts": headcounts,
            }
        )


@extend_schema_view(
    create=extend_schema(operation_id="employees_create"),
    list=extend_schema(operation_id="employees_list"),
    retrieve=extend_schema(operation_id="employees_retrieve"),
    update=extend_schema(operation_id="employees_update"),
    partial_update=extend_schema(operation_id="employees_partial_update"),
    destroy=extend_schema(operation_id="employees_destroy"),
)
class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer

    def get_queryset(self):
        # filter queryset based on logged in user
        return self.request.user.employees.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
